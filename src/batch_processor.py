"""
Batch processor for parallel session handling and analysis.
Enables processing multiple frame description files concurrently with progress tracking.
"""

import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from loguru import logger

from .database import DatabaseManager, GPTConfig, ProcessingConfig, SessionStatus, WindowStatus
from .enhanced_window_processor import EnhancedWindowProcessor
from .context_manager import ContextManager
from .gpt5_client import GPT5Client


@dataclass
class BatchJobConfig:
    name: str
    input_files: List[str]
    gpt_config: GPTConfig
    processing_config: ProcessingConfig
    max_concurrent_sessions: int = 3
    max_retries_per_window: int = 2


@dataclass
class BatchProgress:
    job_id: str
    total_sessions: int
    completed_sessions: int
    failed_sessions: int
    active_sessions: List[str]
    overall_status: str
    start_time: datetime
    estimated_completion: Optional[datetime] = None

    @property
    def completion_percentage(self) -> float:
        if self.total_sessions == 0:
            return 0.0
        return (self.completed_sessions + self.failed_sessions) / self.total_sessions * 100


class BatchProcessor:
    """Handles batch processing of multiple frame description files."""

    def __init__(self, db_manager: DatabaseManager, api_key: str):
        self.db_manager = db_manager
        self.api_key = api_key
        self.active_jobs: Dict[str, BatchProgress] = {}
        self.executor = ThreadPoolExecutor(max_workers=5)

    async def start_batch_job(
        self,
        job_config: BatchJobConfig,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ) -> str:
        """Start a batch processing job with multiple sessions."""

        job_id = str(uuid.uuid4())

        # Validate input files
        valid_files = []
        for file_path in job_config.input_files:
            if not os.path.exists(file_path):
                logger.warning(f"Input file not found: {file_path}")
                continue

            # Validate JSON structure
            processor = EnhancedWindowProcessor()
            is_valid, message = processor.validate_json_structure(file_path)
            if not is_valid:
                logger.warning(f"Invalid JSON structure in {file_path}: {message}")
                continue

            valid_files.append(file_path)

        if not valid_files:
            raise ValueError("No valid input files found")

        # Initialize batch progress
        batch_progress = BatchProgress(
            job_id=job_id,
            total_sessions=len(valid_files),
            completed_sessions=0,
            failed_sessions=0,
            active_sessions=[],
            overall_status="starting",
            start_time=datetime.now()
        )

        self.active_jobs[job_id] = batch_progress

        logger.info(f"Starting batch job {job_id} with {len(valid_files)} sessions")

        # Start processing in background
        asyncio.create_task(
            self._process_batch_async(job_id, job_config, valid_files, progress_callback)
        )

        return job_id

    async def _process_batch_async(
        self,
        job_id: str,
        job_config: BatchJobConfig,
        input_files: List[str],
        progress_callback: Optional[Callable[[BatchProgress], None]] = None
    ):
        """Process multiple sessions in parallel."""

        batch_progress = self.active_jobs[job_id]
        batch_progress.overall_status = "processing"

        # Create semaphore to limit concurrent sessions
        semaphore = asyncio.Semaphore(job_config.max_concurrent_sessions)

        # Create tasks for all sessions
        tasks = []
        for file_path in input_files:
            task = asyncio.create_task(
                self._process_single_session_with_semaphore(
                    semaphore, job_id, file_path, job_config
                )
            )
            tasks.append(task)

        # Process sessions with progress updates
        for completed_task in asyncio.as_completed(tasks):
            try:
                session_result = await completed_task

                if session_result['success']:
                    batch_progress.completed_sessions += 1
                    logger.info(f"Completed session: {session_result['session_id']}")
                else:
                    batch_progress.failed_sessions += 1
                    logger.error(f"Failed session: {session_result.get('error', 'Unknown error')}")

                # Update active sessions list
                if session_result['session_id'] in batch_progress.active_sessions:
                    batch_progress.active_sessions.remove(session_result['session_id'])

                # Call progress callback
                if progress_callback:
                    progress_callback(batch_progress)

            except Exception as e:
                batch_progress.failed_sessions += 1
                logger.error(f"Error in batch processing task: {e}")

        # Mark job as completed
        batch_progress.overall_status = "completed" if batch_progress.failed_sessions == 0 else "completed_with_errors"

        logger.info(f"Batch job {job_id} completed: {batch_progress.completed_sessions} successful, {batch_progress.failed_sessions} failed")

    async def _process_single_session_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        job_id: str,
        file_path: str,
        job_config: BatchJobConfig
    ) -> Dict[str, Any]:
        """Process a single session with concurrency control."""

        session_id = None

        async with semaphore:
            try:
                # Create session
                session_id = str(uuid.uuid4())

                # Add to active sessions
                batch_progress = self.active_jobs[job_id]
                batch_progress.active_sessions.append(session_id)

                # Extract session name from file path
                file_name = Path(file_path).stem
                session_name = f"{job_config.name} - {file_name}"

                # Create session in database
                success = self.db_manager.create_session(
                    session_id=session_id,
                    name=session_name,
                    gpt_config=job_config.gpt_config,
                    processing_config=job_config.processing_config,
                    input_file_path=file_path
                )

                if not success:
                    return {
                        'success': False,
                        'session_id': session_id,
                        'error': 'Failed to create session in database'
                    }

                # Process the session
                result = await self._process_session_windows(
                    session_id, file_path, job_config
                )

                return {
                    'success': result,
                    'session_id': session_id,
                    'file_path': file_path
                }

            except Exception as e:
                logger.error(f"Error processing session {session_id}: {e}")
                return {
                    'success': False,
                    'session_id': session_id,
                    'error': str(e)
                }

    async def _process_session_windows(
        self,
        session_id: str,
        file_path: str,
        job_config: BatchJobConfig
    ) -> bool:
        """Process all windows for a single session."""

        try:
            # Initialize processors
            window_processor = EnhancedWindowProcessor(
                window_seconds=job_config.processing_config.window_seconds
            )
            context_manager = ContextManager(self.db_manager)
            gpt5_client = GPT5Client(self.api_key)

            # Update session status
            self.db_manager.update_session_status(session_id, SessionStatus.PROCESSING)

            # Load and process windows
            frame_descriptions, metadata = window_processor.load_frame_descriptions_from_json(file_path)
            windows = window_processor.create_windows_from_frames(frame_descriptions)

            logger.info(f"Processing {len(windows)} windows for session {session_id}")

            # Process each window
            completed_windows = 0
            for i, window in enumerate(windows, 1):
                window_id = f"{session_id}_window_{i}"

                try:
                    # Create window in database
                    self.db_manager.create_window(
                        window_id=window_id,
                        session_id=session_id,
                        window_number=i,
                        start_time=window.start_time,
                        end_time=window.end_time,
                        input_data=window.to_dict()
                    )

                    # Build context
                    context_prompt = context_manager.build_context_for_window(
                        session_id, i, window
                    )

                    # Analyze with GPT-5 (with retries)
                    analysis_result = None
                    last_error = None

                    for retry in range(job_config.max_retries_per_window + 1):
                        try:
                            analysis_result = await gpt5_client.analyze_window_with_context(
                                system_prompt=job_config.processing_config.system_prompt,
                                context_prompt=context_prompt,
                                window_data=window.to_dict(),
                                config=job_config.gpt_config
                            )
                            break
                        except Exception as e:
                            last_error = e
                            if retry < job_config.max_retries_per_window:
                                logger.warning(f"Retry {retry + 1} for window {i} in session {session_id}: {e}")
                                await asyncio.sleep(2 ** retry)  # Exponential backoff
                            else:
                                logger.error(f"Failed to analyze window {i} after {job_config.max_retries_per_window} retries: {e}")

                    if analysis_result:
                        # Save successful result
                        self.db_manager.update_window_status(
                            window_id=window_id,
                            status=WindowStatus.COMPLETED,
                            output_data=analysis_result.to_dict(),
                            processing_time=analysis_result.processing_time_seconds
                        )

                        # Save context and recommendations
                        context_manager.save_window_context(
                            session_id=session_id,
                            window_number=i,
                            window_context=window_processor.extract_window_context(window),
                            analysis_result=analysis_result.content
                        )

                        completed_windows += 1
                    else:
                        # Save failed result
                        self.db_manager.update_window_status(
                            window_id=window_id,
                            status=WindowStatus.FAILED,
                            error_message=str(last_error) if last_error else "Unknown error"
                        )

                    # Update session progress
                    self.db_manager.update_session_status(
                        session_id, SessionStatus.PROCESSING, completed_windows=completed_windows
                    )

                except Exception as e:
                    logger.error(f"Error processing window {i} in session {session_id}: {e}")

            # Mark session as completed
            final_status = SessionStatus.COMPLETED if completed_windows == len(windows) else SessionStatus.FAILED
            self.db_manager.update_session_status(
                session_id, final_status, completed_windows=completed_windows
            )

            logger.info(f"Session {session_id} completed: {completed_windows}/{len(windows)} windows processed")
            return completed_windows > 0

        except Exception as e:
            logger.error(f"Error processing session {session_id}: {e}")
            self.db_manager.update_session_status(session_id, SessionStatus.FAILED)
            return False

    def get_batch_status(self, job_id: str) -> Optional[BatchProgress]:
        """Get the current status of a batch job."""
        return self.active_jobs.get(job_id)

    def cancel_batch_job(self, job_id: str) -> bool:
        """Cancel a running batch job."""
        if job_id not in self.active_jobs:
            return False

        batch_progress = self.active_jobs[job_id]
        batch_progress.overall_status = "cancelled"

        # Mark active sessions as paused
        for session_id in batch_progress.active_sessions:
            self.db_manager.update_session_status(session_id, SessionStatus.PAUSED)

        logger.info(f"Cancelled batch job {job_id}")
        return True

    def get_all_active_jobs(self) -> List[BatchProgress]:
        """Get all currently active batch jobs."""
        return list(self.active_jobs.values())

    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Remove completed jobs older than specified hours."""
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, progress in self.active_jobs.items():
            if progress.overall_status in ["completed", "completed_with_errors", "cancelled"]:
                age_hours = (current_time - progress.start_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up completed batch job: {job_id}")

    async def estimate_batch_processing_time(
        self,
        input_files: List[str],
        processing_config: ProcessingConfig,
        gpt_config: GPTConfig
    ) -> Dict[str, Any]:
        """Estimate the processing time and cost for a batch job."""

        total_windows = 0
        total_frames = 0
        estimated_tokens = 0

        window_processor = EnhancedWindowProcessor(processing_config.window_seconds)
        gpt5_client = GPT5Client(self.api_key)

        for file_path in input_files:
            if not os.path.exists(file_path):
                continue

            try:
                frame_descriptions, metadata = window_processor.load_frame_descriptions_from_json(file_path)
                windows = window_processor.create_windows_from_frames(frame_descriptions)

                total_windows += len(windows)
                total_frames += len(frame_descriptions)

                # Estimate tokens for first window (as sample)
                if windows:
                    context_manager = ContextManager(self.db_manager)
                    context_prompt = context_manager.build_context_for_window("sample", 1, windows[0])
                    token_estimate = gpt5_client.estimate_token_usage(
                        processing_config.system_prompt,
                        context_prompt,
                        windows[0].to_dict()
                    )
                    estimated_tokens += token_estimate['estimated_total_tokens'] * len(windows)

            except Exception as e:
                logger.warning(f"Could not estimate for {file_path}: {e}")

        # Estimate processing time (rough approximation)
        avg_processing_time_per_window = 30  # seconds
        estimated_total_time_seconds = total_windows * avg_processing_time_per_window

        # Estimate cost
        estimated_cost = gpt5_client.calculate_estimated_cost(
            {'estimated_total_tokens': estimated_tokens},
            gpt_config.model
        )

        return {
            'total_sessions': len([f for f in input_files if os.path.exists(f)]),
            'total_windows': total_windows,
            'total_frames': total_frames,
            'estimated_processing_time_minutes': estimated_total_time_seconds / 60,
            'estimated_tokens': estimated_tokens,
            'estimated_cost_usd': estimated_cost
        }