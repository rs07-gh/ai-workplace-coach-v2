"""
Window Manager - Handles sliding window context and summarization.
Builds context prompts with previous window memory and continuity.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from .utils import setup_logging, format_timestamp
from .frame_processor import Window, Frame

logger = setup_logging(__name__)

class WindowManager:
    """Manages sliding window context and summarization for coaching analysis."""

    def __init__(self):
        self.logger = logger

    def build_context_prompt(
        self,
        window: Window,
        previous_context: Optional[str] = None
    ) -> str:
        """
        Build context prompt for a window including previous context.

        Args:
            window: Current window to analyze
            previous_context: Summary of previous windows

        Returns:
            Formatted context prompt string
        """
        try:
            self.logger.info(f"Building context prompt for window {window.index}")

            prompt_parts = []

            # Header
            prompt_parts.append(f"## Window {window.index + 1} Analysis Context\n")

            # Window metadata
            prompt_parts.append(f"**Time Range:** {self._format_time_range(window.start_time, window.end_time)}")
            prompt_parts.append(f"**Duration:** {window.duration:.1f} seconds")
            prompt_parts.append(f"**Frame Count:** {window.frame_count} frames\n")

            # Previous context
            if previous_context and previous_context.strip():
                prompt_parts.append("## Previous Session Context\n")
                prompt_parts.append(previous_context.strip())
                prompt_parts.append("\n---\n")

            # Current window summary
            if window.summary:
                prompt_parts.append("## Current Window Summary\n")
                prompt_parts.append(self._format_window_summary(window.summary))
                prompt_parts.append("")

            # Detailed frame descriptions
            prompt_parts.append("## Detailed Frame Descriptions\n")
            prompt_parts.append(self._format_frame_descriptions(window.frames))

            # Analysis guidelines
            prompt_parts.append("## Analysis Guidelines\n")
            prompt_parts.append("- Focus on actionable productivity improvements")
            prompt_parts.append("- Reference specific timestamps for evidence")
            prompt_parts.append("- Consider the previous context for continuity")
            prompt_parts.append("- Identify inefficiencies and optimization opportunities")
            prompt_parts.append("- Provide concrete implementation steps")

            context_prompt = "\n".join(prompt_parts)

            self.logger.info(f"Context prompt built successfully ({len(context_prompt)} characters)")
            return context_prompt

        except Exception as error:
            self.logger.error(f"Context prompt building error: {error}")
            raise ValueError(f"Failed to build context prompt: {error}")

    def _format_time_range(self, start_time: float, end_time: float) -> str:
        """Format time range for display."""
        return f"{format_timestamp(start_time)} - {format_timestamp(end_time)}"

    def _format_window_summary(self, summary) -> str:
        """Format window summary for context prompt."""
        summary_lines = []

        if summary.applications:
            summary_lines.append(f"**Applications Used:** {', '.join(summary.applications)}")

        if summary.main_activities:
            summary_lines.append(f"**Main Activities:** {', '.join(summary.main_activities)}")

        if summary.key_descriptions:
            summary_lines.append("**Key Actions:**")
            for desc in summary.key_descriptions:
                summary_lines.append(f"- {desc}")

        return "\n".join(summary_lines)

    def _format_frame_descriptions(self, frames: List[Frame]) -> str:
        """Format frame descriptions with timestamps."""
        if not frames:
            return "No frame descriptions available."

        description_lines = []
        for frame in frames:
            timestamp = format_timestamp(frame.timestamp)
            description = frame.description or "No description"

            description_lines.append(f"**[{timestamp}]** {description}")

            # Add additional metadata if available
            if frame.application:
                description_lines.append(f" *Application: {frame.application}*")
            if frame.window_title:
                description_lines.append(f" *Window: {frame.window_title}*")

            description_lines.append("")  # Empty line for spacing

        return "\n".join(description_lines)

    def summarize_window(
        self,
        window: Window,
        recommendation: Optional[str] = None
    ) -> str:
        """
        Summarize a window and recommendation for next window context.

        Args:
            window: Window to summarize
            recommendation: Optional recommendation text

        Returns:
            Concise summary for context carryover
        """
        try:
            self.logger.info(f"Summarizing window {window.index} for context")

            summary_parts = []

            # Basic window info
            time_range = self._format_time_range(window.start_time, window.end_time)
            summary_parts.append(f"Window {window.index + 1} ({time_range}):")

            # Main activities
            if window.summary and window.summary.main_activities:
                activities = ', '.join(window.summary.main_activities[:2])  # Top 2 activities
                summary_parts.append(f"{activities}.")

            # Key insight from recommendation
            if recommendation:
                key_insight = self._extract_key_insight(recommendation)
                if key_insight:
                    summary_parts.append(f"Key insight: {key_insight}")

            # Applications used
            if window.summary and window.summary.applications:
                apps = ', '.join(window.summary.applications[:2])  # Top 2 apps
                summary_parts.append(f"(Used: {apps})")

            summary = " ".join(summary_parts)

            # Truncate if too long
            if len(summary) > 300:
                summary = summary[:300] + "..."

            self.logger.info(f"Window summary created: {len(summary)} characters")
            return summary

        except Exception as error:
            self.logger.error(f"Window summarization error: {error}")
            return f"Window {window.index + 1}: Processing completed"

    def _extract_key_insight(self, recommendation: str) -> Optional[str]:
        """Extract key insight from recommendation text."""
        if not recommendation or not isinstance(recommendation, str):
            return None

        try:
            # Look for insight patterns
            insight_patterns = [
                r'(?:recommend|suggest|should|could)\s+([^.!?]{20,100})',
                r'(?:opportunity to|can improve by|consider)\s+([^.!?]{20,100})',
                r'(?:inefficiency|bottleneck|delay)\s+([^.!?]{20,100})',
                r'(?:optimize|automate|streamline)\s+([^.!?]{20,100})'
            ]

            for pattern in insight_patterns:
                match = re.search(pattern, recommendation, re.IGNORECASE)
                if match and match.group(1):
                    return match.group(1).strip()

            # Fallback: use first substantial sentence
            sentences = re.split(r'[.!?]+', recommendation)
            for sentence in sentences:
                sentence = sentence.strip()
                if 20 <= len(sentence) <= 150:
                    return sentence

            # Last resort: truncate beginning
            return recommendation[:100].strip() + "..."

        except Exception as error:
            self.logger.error(f"Insight extraction error: {error}")
            return None

    def build_sliding_context(
        self,
        all_windows: List[Window],
        current_window_index: int,
        max_context_windows: int = 3
    ) -> str:
        """
        Build sliding window context with memory management.

        Args:
            all_windows: All available windows
            current_window_index: Index of current window being processed
            max_context_windows: Maximum number of previous windows to include

        Returns:
            Sliding context summary string
        """
        try:
            if current_window_index == 0:
                return ""

            # Calculate context window range
            start_index = max(0, current_window_index - max_context_windows)
            previous_windows = all_windows[start_index:current_window_index]

            if not previous_windows:
                return ""

            context_lines = []

            # Add previous window summaries
            for i, window in enumerate(previous_windows):
                actual_index = start_index + i
                context_lines.append(
                    f"**Previous Window {actual_index + 1}:** {self.summarize_window(window)}"
                )

            # Add contextual continuity
            current_window = all_windows[current_window_index]
            continuity = self._create_contextual_continuity(previous_windows, current_window)
            if continuity:
                context_lines.append("\n**Context Flow:**")
                context_lines.append(continuity)

            return "\n".join(context_lines)

        except Exception as error:
            self.logger.error(f"Sliding context error: {error}")
            return ""

    def _create_contextual_continuity(
        self,
        previous_windows: List[Window],
        current_window: Window
    ) -> str:
        """Create contextual continuity between windows."""
        try:
            if not previous_windows:
                return ""

            continuity_lines = []

            # Track application flow
            app_flow = self._track_application_flow(previous_windows, current_window)
            if app_flow:
                continuity_lines.append(f"Application flow: {app_flow}")

            # Track activity patterns
            activity_pattern = self._track_activity_pattern(previous_windows, current_window)
            if activity_pattern:
                continuity_lines.append(f"Activity pattern: {activity_pattern}")

            # Identify workflow context
            workflow_context = self._identify_workflow_context(previous_windows, current_window)
            if workflow_context:
                continuity_lines.append(f"Workflow context: {workflow_context}")

            return "\n".join(continuity_lines)

        except Exception as error:
            self.logger.error(f"Contextual continuity error: {error}")
            return ""

    def _track_application_flow(
        self,
        previous_windows: List[Window],
        current_window: Window
    ) -> Optional[str]:
        """Track application usage flow across windows."""
        try:
            apps = []

            # Collect apps from previous windows
            for window in previous_windows:
                if window.summary and window.summary.applications:
                    apps.extend(window.summary.applications)

            # Add current window apps
            if current_window.summary and current_window.summary.applications:
                apps.extend(current_window.summary.applications)

            if len(set(apps)) > 1:
                # Get unique apps in order, keeping last 4
                unique_apps = []
                for app in reversed(apps):
                    if app not in unique_apps:
                        unique_apps.insert(0, app)
                        if len(unique_apps) >= 4:
                            break

                return " → ".join(unique_apps)

            return None

        except Exception as error:
            self.logger.error(f"Application flow tracking error: {error}")
            return None

    def _track_activity_pattern(
        self,
        previous_windows: List[Window],
        current_window: Window
    ) -> Optional[str]:
        """Track activity patterns across windows."""
        try:
            activities = []

            # Collect activities from all windows
            for window in previous_windows + [current_window]:
                if window.summary and window.summary.main_activities:
                    activities.extend(window.summary.main_activities)

            if not activities:
                return None

            # Clean activity names (remove counts like "(3x)")
            clean_activities = []
            for activity in activities:
                clean_activity = re.sub(r'\s*\(\d+x\)', '', activity)
                clean_activities.append(clean_activity)

            # Count activity frequency
            activity_counts = {}
            for activity in clean_activities:
                activity_counts[activity] = activity_counts.get(activity, 0) + 1

            # Get top 2 activities
            sorted_activities = sorted(
                activity_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )

            if sorted_activities:
                top_activities = [activity for activity, count in sorted_activities[:2]]
                return " + ".join(top_activities)

            return None

        except Exception as error:
            self.logger.error(f"Activity pattern tracking error: {error}")
            return None

    def _identify_workflow_context(
        self,
        previous_windows: List[Window],
        current_window: Window
    ) -> Optional[str]:
        """Identify overall workflow context from frame descriptions."""
        try:
            # Collect all frame descriptions
            all_descriptions = []
            for window in previous_windows + [current_window]:
                for frame in window.frames:
                    if frame.description:
                        all_descriptions.append(frame.description.lower())

            if not all_descriptions:
                return None

            # Join all descriptions
            combined_text = " ".join(all_descriptions)

            # Define workflow patterns
            workflow_patterns = [
                (r'email|message|communication|slack|teams', 'Communication workflow'),
                (r'document|editing|writing|word|google docs', 'Document creation workflow'),
                (r'research|search|browse|google|wikipedia', 'Research workflow'),
                (r'meeting|call|video|zoom|webex', 'Meeting workflow'),
                (r'data|analysis|spreadsheet|excel|sheets', 'Data analysis workflow'),
                (r'code|programming|develop|github|vscode', 'Development workflow'),
                (r'design|figma|sketch|photoshop|creative', 'Design workflow'),
                (r'project|task|manage|jira|asana|trello', 'Project management workflow')
            ]

            # Check for patterns
            for pattern, context in workflow_patterns:
                matches = re.findall(pattern, combined_text)
                if len(matches) >= 3:  # Require multiple mentions
                    return context

            return None

        except Exception as error:
            self.logger.error(f"Workflow context identification error: {error}")
            return None