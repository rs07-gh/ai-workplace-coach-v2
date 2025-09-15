"""
Coaching Engine - Main orchestration for AI performance coaching analysis.
Coordinates frame processing, window analysis, and recommendation generation.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass

from .config import Config
from .utils import setup_logging, safe_json_stringify, create_output_filename, ensure_output_dir
from .frame_processor import FrameProcessor, Window
from .prompt_manager import PromptManager
from .window_manager import WindowManager
from .api_client import APIClient

logger = setup_logging(__name__)

@dataclass
class RecommendationResult:
    """Result from a single window analysis."""
    window_index: int
    window_start_time: float
    window_end_time: float
    recommendation: str
    previous_context: str
    confidence: float
    processing_time: int
    model_used: str
    tokens_used: int
    search_results: List[Dict[str, Any]]
    tool_calls: int
    timestamp: datetime
    raw_response: Optional[Dict[str, Any]] = None

@dataclass
class AnalysisSession:
    """Complete analysis session results."""
    session_id: str
    total_windows: int
    successful_windows: int
    failed_windows: int
    total_processing_time: int
    recommendations: List[RecommendationResult]
    settings_used: Dict[str, Any]
    timestamp: datetime
    frame_count: int
    video_duration: float

class CoachingEngine:
    """Main coaching analysis engine."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        """
        Initialize coaching engine.

        Args:
            api_key: Optional OpenAI API key override
            progress_callback: Optional callback for progress updates (message, progress_0_to_1)
        """
        self.logger = logger
        self.progress_callback = progress_callback

        # Initialize components
        self.frame_processor = FrameProcessor()
        self.prompt_manager = PromptManager()
        self.window_manager = WindowManager()
        self.api_client = APIClient(api_key)

        # Session state
        self.current_session: Optional[AnalysisSession] = None

    def analyze_frames(
        self,
        frame_data: Union[str, Dict, Path],
        interval_minutes: float = None,
        template_type: str = None,
        custom_prompts: Optional[Dict[str, str]] = None,
        api_settings: Optional[Dict[str, Any]] = None
    ) -> AnalysisSession:
        """
        Analyze frame descriptions and generate coaching recommendations.

        Args:
            frame_data: Frame descriptions (JSON string, dict, or file path)
            interval_minutes: Chunking interval in minutes
            template_type: Prompt template to use
            custom_prompts: Custom system/user prompts
            api_settings: API configuration overrides

        Returns:
            AnalysisSession with complete results
        """
        session_start = time.time()
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            self.logger.info(f"Starting coaching analysis session: {session_id}")
            self._update_progress("Initializing analysis session...", 0.0)

            # Load and validate frame data
            if isinstance(frame_data, Path):
                with open(frame_data, 'r', encoding='utf-8') as f:
                    frame_data = f.read()

            # Set up prompts
            self._setup_prompts(template_type, custom_prompts)

            # Process frames
            self._update_progress("Parsing frame descriptions...", 0.1)
            frames = self.frame_processor.parse_frame_descriptions(frame_data)

            # Create windows
            interval = interval_minutes or Config.DEFAULT_INTERVAL_MINUTES
            self._update_progress("Creating analysis windows...", 0.2)
            windows = self.frame_processor.chunk_by_interval(frames, interval)

            self.logger.info(f"Created {len(windows)} windows from {len(frames)} frames")

            # Process windows
            self._update_progress("Generating recommendations...", 0.3)
            recommendations = self._process_windows(windows, api_settings)

            # Create session results
            total_time = int((time.time() - session_start) * 1000)
            video_duration = windows[-1].end_time - windows[0].start_time if windows else 0

            session = AnalysisSession(
                session_id=session_id,
                total_windows=len(windows),
                successful_windows=len([r for r in recommendations if not r.recommendation.startswith('ERROR:')]),
                failed_windows=len([r for r in recommendations if r.recommendation.startswith('ERROR:')]),
                total_processing_time=total_time,
                recommendations=recommendations,
                settings_used=self._get_session_settings(api_settings),
                timestamp=datetime.now(),
                frame_count=len(frames),
                video_duration=video_duration
            )

            self.current_session = session
            self._update_progress("Analysis complete!", 1.0)

            self.logger.info(f"Session {session_id} completed: {session.successful_windows}/{session.total_windows} successful")
            return session

        except Exception as error:
            self.logger.error(f"Analysis session failed: {error}")
            self._update_progress(f"Analysis failed: {error}", 0.0)
            raise error

    def _setup_prompts(
        self,
        template_type: Optional[str],
        custom_prompts: Optional[Dict[str, str]]
    ) -> None:
        """Set up system and user prompts."""

        if custom_prompts:
            if 'system_prompt' in custom_prompts:
                self.prompt_manager.set_system_prompt(custom_prompts['system_prompt'])
            if 'user_prompt' in custom_prompts:
                self.prompt_manager.set_user_prompt(custom_prompts['user_prompt'])
        elif template_type:
            user_prompt = self.prompt_manager.create_user_prompt_from_template(template_type)
            self.prompt_manager.set_user_prompt(user_prompt)

    def _process_windows(
        self,
        windows: List[Window],
        api_settings: Optional[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Process all windows and generate recommendations."""

        recommendations = []
        previous_context = ""

        for i, window in enumerate(windows):
            try:
                progress = 0.3 + (i / len(windows)) * 0.6  # 30% to 90%
                self._update_progress(f"Processing window {i + 1}/{len(windows)}...", progress)

                # Build context prompt
                context_prompt = self.window_manager.build_context_prompt(window, previous_context)

                # Generate recommendation
                system_prompt = self.prompt_manager.get_system_prompt()
                user_prompt = self.prompt_manager.get_user_prompt()

                api_response = self.api_client.generate_recommendation(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    frame_context=context_prompt,
                    settings=api_settings
                )

                # Create result
                result = RecommendationResult(
                    window_index=i,
                    window_start_time=window.start_time,
                    window_end_time=window.end_time,
                    recommendation=api_response['content'],
                    previous_context=previous_context,
                    confidence=api_response.get('confidence', 0.8),
                    processing_time=api_response.get('processing_time', 0),
                    model_used=api_response.get('model', 'gpt-5'),
                    tokens_used=api_response.get('tokens_used', 0),
                    search_results=api_response.get('search_results', []),
                    tool_calls=api_response.get('tool_calls', 0),
                    timestamp=datetime.now(),
                    raw_response=api_response.get('raw_response')
                )

                recommendations.append(result)

                # Update context for next window
                previous_context = self.window_manager.summarize_window(window, api_response['content'])

                # Brief pause to avoid rate limits
                if i < len(windows) - 1:
                    time.sleep(0.5)

            except Exception as error:
                self.logger.error(f"Window {i} processing failed: {error}")

                # Create error result
                error_result = RecommendationResult(
                    window_index=i,
                    window_start_time=window.start_time,
                    window_end_time=window.end_time,
                    recommendation=f"ERROR: {str(error)}",
                    previous_context=previous_context,
                    confidence=0.0,
                    processing_time=0,
                    model_used="error",
                    tokens_used=0,
                    search_results=[],
                    tool_calls=0,
                    timestamp=datetime.now()
                )

                recommendations.append(error_result)

        return recommendations

    def _get_session_settings(self, api_settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get settings used for this session."""

        settings = Config.to_dict()
        if api_settings:
            settings.update(api_settings)

        return settings

    def _update_progress(self, message: str, progress: float) -> None:
        """Update progress via callback if available."""

        self.logger.info(message)
        if self.progress_callback:
            self.progress_callback(message, progress)

    def export_session(
        self,
        session: Optional[AnalysisSession] = None,
        output_format: str = 'json',
        include_raw_responses: bool = False
    ) -> Path:
        """
        Export session results to file.

        Args:
            session: Session to export (uses current if None)
            output_format: Export format ('json', 'csv')
            include_raw_responses: Whether to include raw API responses

        Returns:
            Path to exported file
        """
        session = session or self.current_session
        if not session:
            raise ValueError("No session to export")

        try:
            self.logger.info(f"Exporting session {session.session_id} as {output_format}")

            # Prepare export data
            export_data = self._prepare_export_data(session, include_raw_responses)

            # Create output filename
            filename = create_output_filename(
                prefix=f"coaching_analysis_{session.session_id}",
                extension=output_format
            )

            output_dir = ensure_output_dir("sessions")
            output_path = output_dir / filename

            # Export based on format
            if output_format.lower() == 'json':
                self._export_json(export_data, output_path)
            elif output_format.lower() == 'csv':
                self._export_csv(export_data, output_path)
            else:
                raise ValueError(f"Unsupported export format: {output_format}")

            self.logger.info(f"Session exported to: {output_path}")
            return output_path

        except Exception as error:
            self.logger.error(f"Export failed: {error}")
            raise error

    def _prepare_export_data(
        self,
        session: AnalysisSession,
        include_raw_responses: bool
    ) -> Dict[str, Any]:
        """Prepare session data for export."""

        # Convert recommendations to dict format
        recommendations_data = []
        for rec in session.recommendations:
            rec_data = {
                'window_index': rec.window_index + 1,
                'window_time_range': f"{rec.window_start_time:.1f}s - {rec.window_end_time:.1f}s",
                'recommendation': rec.recommendation,
                'previous_context': rec.previous_context,
                'confidence': rec.confidence,
                'processing_time_ms': rec.processing_time,
                'model_used': rec.model_used,
                'tokens_used': rec.tokens_used,
                'search_results_count': len(rec.search_results),
                'tool_calls': rec.tool_calls,
                'timestamp': rec.timestamp.isoformat(),
                'has_error': rec.recommendation.startswith('ERROR:')
            }

            if include_raw_responses and rec.raw_response:
                rec_data['raw_api_response'] = rec.raw_response

            recommendations_data.append(rec_data)

        return {
            'session_metadata': {
                'session_id': session.session_id,
                'timestamp': session.timestamp.isoformat(),
                'total_windows': session.total_windows,
                'successful_windows': session.successful_windows,
                'failed_windows': session.failed_windows,
                'total_processing_time_ms': session.total_processing_time,
                'frame_count': session.frame_count,
                'video_duration_seconds': session.video_duration,
                'success_rate': session.successful_windows / session.total_windows if session.total_windows > 0 else 0
            },
            'settings_used': session.settings_used,
            'recommendations': recommendations_data
        }

    def _export_json(self, data: Dict[str, Any], output_path: Path) -> None:
        """Export data as JSON."""

        success, json_str, error = safe_json_stringify(data, pretty=True)
        if not success:
            raise ValueError(f"JSON serialization failed: {error}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

    def _export_csv(self, data: Dict[str, Any], output_path: Path) -> None:
        """Export recommendations as CSV."""

        import csv

        recommendations = data['recommendations']
        if not recommendations:
            raise ValueError("No recommendations to export")

        # Get fieldnames from first recommendation
        fieldnames = list(recommendations[0].keys())
        if 'raw_api_response' in fieldnames:
            fieldnames.remove('raw_api_response')  # Too complex for CSV

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rec in recommendations:
                # Create CSV-safe version
                csv_rec = {k: v for k, v in rec.items() if k in fieldnames}
                writer.writerow(csv_rec)

    def get_session_summary(self, session: Optional[AnalysisSession] = None) -> Dict[str, Any]:
        """Get summary statistics for a session."""

        session = session or self.current_session
        if not session:
            return {'error': 'No session available'}

        successful_recs = [r for r in session.recommendations if not r.recommendation.startswith('ERROR:')]

        return {
            'session_id': session.session_id,
            'timestamp': session.timestamp.isoformat(),
            'windows_processed': session.total_windows,
            'success_rate': f"{session.successful_windows}/{session.total_windows} ({session.successful_windows/session.total_windows*100:.1f}%)",
            'total_processing_time': f"{session.total_processing_time/1000:.1f}s",
            'average_processing_time': f"{sum(r.processing_time for r in successful_recs)/len(successful_recs):.0f}ms" if successful_recs else "N/A",
            'total_tokens_used': sum(r.tokens_used for r in successful_recs),
            'total_search_queries': sum(len(r.search_results) for r in successful_recs),
            'video_duration': f"{session.video_duration:.1f}s ({session.video_duration/60:.1f}m)",
            'frames_analyzed': session.frame_count,
            'models_used': list(set(r.model_used for r in successful_recs))
        }

    def test_configuration(self) -> Dict[str, Any]:
        """Test the current configuration."""

        try:
            self.logger.info("Testing coaching engine configuration")

            # Test API connection
            api_test = self.api_client.test_connection()

            # Test frame processing
            test_frames = {
                "frames": [
                    {"timestamp": 0, "description": "Test frame 1"},
                    {"timestamp": 30, "description": "Test frame 2"}
                ]
            }

            try:
                frames = self.frame_processor.parse_frame_descriptions(test_frames)
                windows = self.frame_processor.chunk_by_interval(frames, 1.0)
                frame_test = {
                    'success': True,
                    'frames_parsed': len(frames),
                    'windows_created': len(windows)
                }
            except Exception as e:
                frame_test = {'success': False, 'error': str(e)}

            # Test prompts
            try:
                system_prompt = self.prompt_manager.get_system_prompt()
                user_prompt = self.prompt_manager.get_user_prompt()
                prompt_test = {
                    'success': True,
                    'system_prompt_length': len(system_prompt),
                    'user_prompt_length': len(user_prompt)
                }
            except Exception as e:
                prompt_test = {'success': False, 'error': str(e)}

            return {
                'overall_status': api_test['success'] and frame_test['success'] and prompt_test['success'],
                'api_test': api_test,
                'frame_processing_test': frame_test,
                'prompt_test': prompt_test,
                'configuration': Config.to_dict()
            }

        except Exception as error:
            self.logger.error(f"Configuration test failed: {error}")
            return {
                'overall_status': False,
                'error': str(error)
            }