"""
Frame Processor - Handles parsing and chunking of frame descriptions.
Supports multiple JSON formats and creates time-based windows for analysis.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from .utils import setup_logging, safe_json_parse, parse_time_to_seconds, format_timestamp

logger = setup_logging(__name__)

@dataclass
class Frame:
    """Represents a single frame description."""
    timestamp: float
    description: str
    application: Optional[str] = None
    window_title: Optional[str] = None
    screen_region: Optional[str] = None
    activities: Optional[List[str]] = None
    confidence: Optional[float] = None
    original_index: Optional[int] = None
    duration: float = 0.0

@dataclass
class WindowSummary:
    """Summary information for a window."""
    frame_count: int
    time_span: str
    applications: List[str]
    main_activities: List[str]
    key_descriptions: List[str]

@dataclass
class Window:
    """Represents a time-based window of frames."""
    index: int
    start_time: float
    end_time: float
    duration: float
    frame_count: int
    frames: List[Frame]
    summary: WindowSummary

class FrameProcessor:
    """Processes frame descriptions and creates analysis windows."""

    def __init__(self):
        self.logger = logger

    def parse_frame_descriptions(self, frame_data: Union[str, Dict]) -> List[Frame]:
        """
        Parse frame descriptions from JSON input.
        Supports multiple input formats.

        Args:
            frame_data: JSON string or parsed dictionary

        Returns:
            List of normalized Frame objects

        Raises:
            ValueError: If input format is invalid
        """
        try:
            self.logger.info("Parsing frame descriptions...")

            # Parse JSON if string
            if isinstance(frame_data, str):
                success, parsed_data, error = safe_json_parse(frame_data)
                if not success:
                    raise ValueError(f"Invalid JSON format: {error}")
                data = parsed_data
            else:
                data = frame_data

            # Extract frames from various formats
            frames_list = self._extract_frames_from_data(data)

            if not frames_list:
                raise ValueError("No frames found in the data")

            # Normalize frames
            processed_frames = []
            for i, frame_data in enumerate(frames_list):
                frame = self._normalize_frame(frame_data, i)
                if frame:
                    processed_frames.append(frame)

            # Sort by timestamp
            processed_frames.sort(key=lambda f: f.timestamp)

            self.logger.info(f"Parsed {len(processed_frames)} frames successfully")
            return processed_frames

        except Exception as error:
            self.logger.error(f"Frame parsing error: {error}")
            raise ValueError(f"Failed to parse frame descriptions: {error}")

    def _extract_frames_from_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract frames from various JSON structures."""

        frames_list = []

        # Format 1: {"windows": [{"frames": [...]}]}
        if 'windows' in data:
            for window in data['windows']:
                if 'frames' in window and isinstance(window['frames'], list):
                    frames_list.extend(window['frames'])
                elif 'frame_descriptions' in window:
                    frames_list.extend(window['frame_descriptions'])

        # Format 2: {"intervals": [{"frames": [...]}]}
        elif 'intervals' in data:
            for interval in data['intervals']:
                if 'frames' in interval and isinstance(interval['frames'], list):
                    frames_list.extend(interval['frames'])
                elif 'frame_descriptions' in interval:
                    frames_list.extend(interval['frame_descriptions'])

        # Format 3: {"frames": [...]}
        elif 'frames' in data and isinstance(data['frames'], list):
            frames_list = data['frames']

        # Format 4: Direct array
        elif isinstance(data, list):
            frames_list = data

        # Format 5: Summary-like object (try to extract synthetic frames)
        else:
            synthetic_frames = self._extract_frames_from_summary(data)
            if synthetic_frames:
                frames_list = synthetic_frames

        return frames_list

    def _extract_frames_from_summary(self, obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract synthetic frames from summary-like objects."""

        if not isinstance(obj, dict):
            return []

        frames = []
        timestamp_counter = 0.0

        def add_frame(text: str, label: str = ""):
            nonlocal timestamp_counter
            if text and isinstance(text, str) and text.strip():
                description = f"{label}: {text}" if label else text
                frames.append({
                    'timestamp': timestamp_counter,
                    'description': description.strip()
                })
                timestamp_counter += 1.0

        # Look for common summary keys
        summary_keys = [
            'completed_since_last',
            'key_entities',
            'key_actions',
            'notes',
            'insights',
            'highlights',
            'activities',
            'observations'
        ]

        found_content = False
        for key in summary_keys:
            if key in obj:
                value = obj[key]
                label = key.replace('_', ' ').title()

                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            add_frame(item, label)
                            found_content = True
                        elif isinstance(item, dict):
                            # Extract description-like fields
                            for field in ['description', 'text', 'content']:
                                if field in item and isinstance(item[field], str):
                                    add_frame(item[field], label)
                                    found_content = True
                                    break
                elif isinstance(value, str):
                    add_frame(value, label)
                    found_content = True

        # If no standard keys found, try all keys
        if not found_content:
            for key, value in obj.items():
                if isinstance(value, (str, list)) and key not in ['timestamp', 'time']:
                    label = key.replace('_', ' ').title()
                    if isinstance(value, str):
                        add_frame(value, label)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                add_frame(item, label)

        return frames

    def _normalize_frame(self, frame_data: Dict[str, Any], index: int) -> Optional[Frame]:
        """Normalize frame data to consistent Frame object."""

        try:
            # Extract timestamp
            timestamp = self._extract_timestamp(frame_data, index)
            if timestamp is None:
                self.logger.warning(f"Frame {index} has invalid timestamp")
                return None

            # Extract description
            description = self._extract_description(frame_data)
            if not description:
                self.logger.warning(f"Frame {index} has no description")
                return None

            # Extract optional fields
            application = frame_data.get('application') or frame_data.get('app')
            window_title = frame_data.get('window_title') or frame_data.get('title')
            screen_region = frame_data.get('screen_region') or frame_data.get('region')
            activities = frame_data.get('activities')
            confidence = frame_data.get('confidence')
            duration = float(frame_data.get('duration', 0))

            return Frame(
                timestamp=timestamp,
                description=description,
                application=application,
                window_title=window_title,
                screen_region=screen_region,
                activities=activities if isinstance(activities, list) else None,
                confidence=confidence,
                original_index=index,
                duration=duration
            )

        except Exception as error:
            self.logger.error(f"Frame normalization error for index {index}: {error}")
            return None

    def _extract_timestamp(self, frame_data: Dict[str, Any], index: int) -> Optional[float]:
        """Extract timestamp from frame data."""

        # Try different timestamp fields
        timestamp_fields = ['timestamp', 'time', 'seconds', 'frame_time']

        for field in timestamp_fields:
            if field in frame_data:
                return parse_time_to_seconds(frame_data[field])

        # If no timestamp field found, use index as fallback
        self.logger.warning(f"No timestamp found for frame {index}, using index")
        return float(index)

    def _extract_description(self, frame_data: Dict[str, Any]) -> str:
        """Extract description from frame data."""

        # Try different description fields
        description_fields = [
            'description',
            'forensic_description',
            'frame_description',
            'content',
            'text'
        ]

        for field in description_fields:
            if field in frame_data and frame_data[field]:
                return str(frame_data[field]).strip()

        return ""

    def chunk_by_interval(
        self,
        frames: List[Frame],
        interval_minutes: float
    ) -> List[Window]:
        """
        Chunk frames into time-based intervals.

        Args:
            frames: List of Frame objects
            interval_minutes: Interval duration in minutes

        Returns:
            List of Window objects
        """
        try:
            self.logger.info(f"Chunking {len(frames)} frames by {interval_minutes} minute intervals")

            if not frames:
                raise ValueError("No frames to chunk")

            interval_seconds = interval_minutes * 60
            windows = []

            # Calculate time span
            start_time = frames[0].timestamp
            end_time = frames[-1].timestamp
            total_duration = end_time - start_time

            self.logger.info(f"Video duration: {total_duration:.1f} seconds ({total_duration/60:.2f} minutes)")

            # Create windows
            window_start = start_time
            window_index = 0

            while window_start < end_time:
                window_end = min(window_start + interval_seconds, end_time)

                # Get frames for this window
                window_frames = [
                    f for f in frames
                    if window_start <= f.timestamp < window_end
                ]

                if window_frames:
                    # Create window summary
                    summary = self._create_window_summary(window_frames)

                    window = Window(
                        index=window_index,
                        start_time=window_start,
                        end_time=window_end,
                        duration=window_end - window_start,
                        frame_count=len(window_frames),
                        frames=window_frames,
                        summary=summary
                    )

                    windows.append(window)
                    window_index += 1

                window_start = window_end

            self.logger.info(f"Created {len(windows)} windows from {len(frames)} frames")
            return windows

        except Exception as error:
            self.logger.error(f"Chunking error: {error}")
            raise ValueError(f"Failed to chunk frames: {error}")

    def _create_window_summary(self, frames: List[Frame]) -> WindowSummary:
        """Create summary for a window."""

        if not frames:
            return WindowSummary(
                frame_count=0,
                time_span="N/A",
                applications=[],
                main_activities=[],
                key_descriptions=[]
            )

        try:
            # Collect applications
            applications = set()
            for frame in frames:
                if frame.application:
                    applications.add(frame.application)

                # Try to extract app names from descriptions
                app_patterns = [
                    r'(?:in |on |using |with )([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:window|application|app)',
                ]

                for pattern in app_patterns:
                    import re
                    matches = re.findall(pattern, frame.description)
                    applications.update(matches)

            # Extract main activities
            main_activities = self._extract_main_activities(frames)

            # Get key descriptions
            key_descriptions = self._extract_key_descriptions(frames)

            # Format time span
            time_span = f"{format_timestamp(frames[0].timestamp)} - {format_timestamp(frames[-1].timestamp)}"

            return WindowSummary(
                frame_count=len(frames),
                time_span=time_span,
                applications=list(applications),
                main_activities=main_activities,
                key_descriptions=key_descriptions
            )

        except Exception as error:
            self.logger.error(f"Window summary error: {error}")
            return WindowSummary(
                frame_count=len(frames),
                time_span="Unknown",
                applications=[],
                main_activities=[],
                key_descriptions=[]
            )

    def _extract_main_activities(self, frames: List[Frame]) -> List[str]:
        """Extract main activities from frame descriptions."""

        activity_counts = {}
        activity_patterns = [
            (r'typing|writing|entering', 'typing'),
            (r'clicking|selecting|choosing', 'clicking'),
            (r'scrolling|navigating|browsing', 'scrolling'),
            (r'reading|reviewing|viewing', 'reading'),
            (r'searching|finding|looking', 'searching'),
            (r'copying|pasting|moving', 'copying'),
            (r'opening|closing|switching', 'opening'),
            (r'editing|modifying|changing', 'editing'),
        ]

        for frame in frames:
            # Safely handle description as string
            description = str(frame.description) if frame.description else ''
            description = description.lower()
            for pattern, activity in activity_patterns:
                import re
                if re.search(pattern, description):
                    activity_counts[activity] = activity_counts.get(activity, 0) + 1

        # Sort by frequency and return top 3
        sorted_activities = sorted(
            activity_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [f"{activity} ({count}x)" for activity, count in sorted_activities[:3]]

    def _extract_key_descriptions(self, frames: List[Frame]) -> List[str]:
        """Extract key descriptions for context."""

        key_descriptions = []

        # Always include first and last frames
        if frames:
            key_descriptions.append(frames[0].description[:150])
            if len(frames) > 1:
                key_descriptions.append(frames[-1].description[:150])

        # Include longer descriptions (likely more detailed)
        for frame in frames:
            if (len(frame.description) > 100 and
                frame.description not in key_descriptions and
                len(key_descriptions) < 5):
                desc = frame.description[:150]
                if len(frame.description) > 150:
                    desc += "..."
                key_descriptions.append(desc)

        return key_descriptions[:5]

    def validate_frame_data(self, frame_data: Union[str, Dict]) -> Dict[str, Any]:
        """
        Validate frame data structure.

        Returns:
            Dictionary with validation results
        """
        try:
            # Parse if string
            if isinstance(frame_data, str):
                success, data, error = safe_json_parse(frame_data)
                if not success:
                    return {
                        'valid': False,
                        'frame_count': 0,
                        'has_timestamps': False,
                        'has_descriptions': False,
                        'errors': [f'JSON parse error: {error}']
                    }
            else:
                data = frame_data

            # Extract frames
            frames_list = self._extract_frames_from_data(data)

            # Validate structure
            frame_count = len(frames_list)
            has_timestamps = False
            has_descriptions = False
            errors = []

            if frame_count == 0:
                errors.append("No frames found in data")
            else:
                # Check first frame for required fields
                first_frame = frames_list[0]
                timestamp_fields = ['timestamp', 'time', 'seconds', 'frame_time']
                description_fields = ['description', 'forensic_description', 'frame_description', 'content', 'text']

                has_timestamps = any(field in first_frame for field in timestamp_fields)
                has_descriptions = any(field in first_frame and first_frame[field] for field in description_fields)

                if not has_timestamps:
                    errors.append("Frames missing timestamp fields")
                if not has_descriptions:
                    errors.append("Frames missing description fields")

            return {
                'valid': len(errors) == 0,
                'frame_count': frame_count,
                'has_timestamps': has_timestamps,
                'has_descriptions': has_descriptions,
                'errors': errors
            }

        except Exception as error:
            return {
                'valid': False,
                'frame_count': 0,
                'has_timestamps': False,
                'has_descriptions': False,
                'errors': [f'Validation error: {error}']
            }