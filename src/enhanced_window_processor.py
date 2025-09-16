"""
Enhanced window processor with time-based windowing and comprehensive context extraction.
Integrates with the existing frame processor for backward compatibility.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class FrameDescription:
    timestamp: str
    forensic_description: str
    applications: List[str]
    ui_elements: List[str]
    user_actions: List[str]
    raw_timestamp_seconds: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FrameDescription':
        return cls(
            timestamp=data.get('timestamp', ''),
            forensic_description=data.get('forensic_description', ''),
            applications=data.get('applications', []),
            ui_elements=data.get('ui_elements', []),
            user_actions=data.get('user_actions', []),
            raw_timestamp_seconds=data.get('raw_timestamp_seconds', 0.0)
        )


@dataclass
class ProcessingWindow:
    window_number: int
    start_time: float
    end_time: float
    frame_descriptions: List[FrameDescription]
    window_analysis: Dict[str, Any] = None

    def get_duration(self) -> float:
        return self.end_time - self.start_time

    def get_frame_count(self) -> int:
        return len(self.frame_descriptions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'window_number': self.window_number,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.get_duration(),
            'frame_count': self.get_frame_count(),
            'frame_descriptions': [
                {
                    'timestamp': fd.timestamp,
                    'forensic_description': fd.forensic_description,
                    'applications': fd.applications,
                    'ui_elements': fd.ui_elements,
                    'user_actions': fd.user_actions,
                    'raw_timestamp_seconds': fd.raw_timestamp_seconds
                }
                for fd in self.frame_descriptions
            ],
            'window_analysis': self.window_analysis
        }


class EnhancedWindowProcessor:
    """Enhanced window processor with time-based windowing."""

    def __init__(self, window_seconds: int = 30):
        self.window_seconds = window_seconds

    @staticmethod
    def parse_timestamp_to_seconds(timestamp: str) -> float:
        """Convert timestamp string (HH:MM:SS or MM:SS) to seconds."""
        try:
            parts = timestamp.split(':')
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(float, parts)
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS
                minutes, seconds = map(float, parts)
                return minutes * 60 + seconds
            else:  # Just seconds
                return float(timestamp)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse timestamp '{timestamp}': {e}")
            return 0.0

    def load_frame_descriptions_from_json(self, json_file_path: str) -> Tuple[List[FrameDescription], Dict[str, Any]]:
        """Load frame descriptions from a JSON file and extract metadata."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract metadata
            metadata = {
                'video': data.get('video', ''),
                'duration_seconds': data.get('duration_seconds', 0),
                'fps': data.get('fps', 1),
                'window_seconds': data.get('window_seconds', 30),
                'model': data.get('model', ''),
                'processing_method': data.get('processing_method', ''),
                'total_windows': len(data.get('windows', []))
            }

            # Extract frame descriptions from all windows
            frame_descriptions = []
            windows_data = data.get('windows', [])

            for window_data in windows_data:
                window_frames = window_data.get('frame_descriptions', [])

                for frame_data in window_frames:
                    if not isinstance(frame_data, dict):
                        logger.warning(f"Skipping invalid frame data: {type(frame_data)}")
                        continue
                    timestamp_seconds = self.parse_timestamp_to_seconds(frame_data.get('timestamp', '00:00:00'))

                    frame_desc = FrameDescription.from_dict(frame_data)
                    frame_desc.raw_timestamp_seconds = timestamp_seconds
                    frame_descriptions.append(frame_desc)

            # Sort by timestamp
            frame_descriptions.sort(key=lambda x: x.raw_timestamp_seconds)

            logger.info(f"Loaded {len(frame_descriptions)} frame descriptions from {json_file_path}")
            return frame_descriptions, metadata

        except Exception as e:
            logger.error(f"Failed to load frame descriptions from {json_file_path}: {e}")
            raise

    def create_windows_from_frames(self, frame_descriptions: List[FrameDescription]) -> List[ProcessingWindow]:
        """Create time-based windows from frame descriptions."""
        if not frame_descriptions:
            return []

        windows = []
        current_window_start = 0.0
        window_number = 1

        while True:
            window_end = current_window_start + self.window_seconds

            # Find frames within this window
            window_frames = [
                frame for frame in frame_descriptions
                if current_window_start <= frame.raw_timestamp_seconds < window_end
            ]

            # If no frames in this window and we're beyond all frames, break
            if not window_frames:
                max_timestamp = max(frame.raw_timestamp_seconds for frame in frame_descriptions) if frame_descriptions else 0
                if current_window_start >= max_timestamp:
                    break

            # Create window even if it has no frames (for completeness)
            window = ProcessingWindow(
                window_number=window_number,
                start_time=current_window_start,
                end_time=window_end,
                frame_descriptions=window_frames
            )

            windows.append(window)

            current_window_start = window_end
            window_number += 1

            # Safety check to prevent infinite loops
            if window_number > 1000:  # Reasonable upper limit
                logger.warning("Reached maximum window limit, stopping window creation")
                break

        logger.info(f"Created {len(windows)} windows with {self.window_seconds}s duration each")
        return windows

    def extract_window_context(self, window: ProcessingWindow) -> Dict[str, Any]:
        """Extract contextual information from a window for summarization."""
        if not window.frame_descriptions:
            return {
                'applications_used': [],
                'ui_elements_interacted': [],
                'user_actions_performed': [],
                'workflow_summary': "No activity detected in this window"
            }

        # Aggregate information across all frames in the window
        all_applications = set()
        all_ui_elements = set()
        all_user_actions = set()
        key_activities = []

        for frame in window.frame_descriptions:
            all_applications.update(frame.applications)
            all_ui_elements.update(frame.ui_elements)
            all_user_actions.update(frame.user_actions)

            # Extract key activities from forensic descriptions
            if frame.forensic_description and len(frame.forensic_description) > 50:
                key_activities.append(frame.forensic_description[:200] + "...")

        # Generate a summary of the workflow for this window
        workflow_summary = self._generate_workflow_summary(
            list(all_applications),
            list(all_user_actions),
            key_activities
        )

        return {
            'applications_used': list(all_applications),
            'ui_elements_interacted': list(all_ui_elements),
            'user_actions_performed': list(all_user_actions),
            'workflow_summary': workflow_summary,
            'frame_count': len(window.frame_descriptions),
            'time_range': f"{window.start_time:.1f}s - {window.end_time:.1f}s"
        }

    def _generate_workflow_summary(self, applications: List[str], user_actions: List[str],
                                 key_activities: List[str]) -> str:
        """Generate a concise workflow summary from extracted information."""
        if not applications and not user_actions:
            return "No significant activity detected"

        summary_parts = []

        if applications:
            apps_text = ", ".join(applications[:3])  # Limit to top 3 apps
            if len(applications) > 3:
                apps_text += f" and {len(applications) - 3} others"
            summary_parts.append(f"Working in {apps_text}")

        if user_actions:
            # Prioritize meaningful actions
            meaningful_actions = [action for action in user_actions
                                if not action.startswith('hover') and action != 'idle']
            if meaningful_actions:
                actions_text = ", ".join(meaningful_actions[:3])
                summary_parts.append(f"performing {actions_text}")

        return ". ".join(summary_parts) if summary_parts else "General interface interaction"

    def create_session_from_json(self, json_file_path: str, session_name: str = None) -> Tuple[str, List[ProcessingWindow], Dict[str, Any]]:
        """Create a complete session from a JSON file."""
        # Generate session ID
        session_id = str(uuid.uuid4())

        # Load frame descriptions
        frame_descriptions, metadata = self.load_frame_descriptions_from_json(json_file_path)

        # Create windows
        windows = self.create_windows_from_frames(frame_descriptions)

        # Use provided name or extract from metadata
        if not session_name:
            video_name = metadata.get('video', 'Unknown Video')
            session_name = f"Analysis of {video_name}"

        # Update metadata
        metadata.update({
            'session_id': session_id,
            'session_name': session_name,
            'total_processing_windows': len(windows),
            'input_file_path': json_file_path
        })

        logger.info(f"Created session {session_id} with {len(windows)} windows from {json_file_path}")

        return session_id, windows, metadata

    def validate_json_structure(self, json_file_path: str) -> Tuple[bool, str]:
        """Validate that a JSON file has the expected structure for processing."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check for required top-level fields
            if 'windows' not in data:
                return False, "Missing 'windows' field in JSON structure"

            windows = data['windows']
            if not isinstance(windows, list) or len(windows) == 0:
                return False, "No windows found in JSON file"

            # Check first window structure
            first_window = windows[0]
            if 'frame_descriptions' not in first_window:
                return False, "Missing 'frame_descriptions' in window structure"

            frame_descriptions = first_window['frame_descriptions']
            if not isinstance(frame_descriptions, list) or len(frame_descriptions) == 0:
                return False, "No frame descriptions found in first window"

            # Check first frame structure
            first_frame = frame_descriptions[0]
            required_fields = ['timestamp', 'forensic_description']
            for field in required_fields:
                if field not in first_frame:
                    return False, f"Missing required field '{field}' in frame description"

            return True, "JSON structure is valid for processing"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
        except Exception as e:
            return False, f"Error validating JSON: {e}"

    def get_processing_stats(self, windows: List[ProcessingWindow]) -> Dict[str, Any]:
        """Get statistics about the processing windows."""
        if not windows:
            return {
                'total_windows': 0,
                'total_frames': 0,
                'total_duration': 0.0,
                'avg_frames_per_window': 0.0,
                'applications_summary': {},
                'time_range': "0.0s - 0.0s"
            }

        total_frames = sum(window.get_frame_count() for window in windows)
        total_duration = windows[-1].end_time - windows[0].start_time

        # Count application usage across all windows
        app_counts = {}
        for window in windows:
            for frame in window.frame_descriptions:
                for app in frame.applications:
                    app_counts[app] = app_counts.get(app, 0) + 1

        return {
            'total_windows': len(windows),
            'total_frames': total_frames,
            'total_duration': total_duration,
            'avg_frames_per_window': total_frames / len(windows) if windows else 0.0,
            'applications_summary': dict(sorted(app_counts.items(), key=lambda x: x[1], reverse=True)),
            'time_range': f"{windows[0].start_time:.1f}s - {windows[-1].end_time:.1f}s"
        }

    def convert_to_legacy_format(self, windows: List[ProcessingWindow]) -> Dict[str, Any]:
        """Convert enhanced windows to legacy format for backward compatibility."""
        legacy_windows = []

        for window in windows:
            legacy_window = {
                'window_analysis': {
                    'window': f"{window.window_number}/{len(windows)}",
                    'time_range': f"{window.start_time:.1f}s-{window.end_time:.1f}s"
                },
                'frame_descriptions': [
                    {
                        'timestamp': frame.timestamp,
                        'forensic_description': frame.forensic_description,
                        'applications': frame.applications,
                        'ui_elements': frame.ui_elements,
                        'user_actions': frame.user_actions
                    }
                    for frame in window.frame_descriptions
                ]
            }
            legacy_windows.append(legacy_window)

        return {
            'windows': legacy_windows,
            'window_seconds': self.window_seconds,
            'total_windows': len(windows)
        }