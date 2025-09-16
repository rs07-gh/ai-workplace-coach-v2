"""
Context manager for maintaining rolling context summaries across windows.
Provides comprehensive context building and recommendation deduplication.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from loguru import logger

from .database import DatabaseManager
from .enhanced_window_processor import ProcessingWindow


@dataclass
class ContextSummary:
    workflow_patterns: List[str]
    tools_used: List[str]
    previous_recommendations: List[str]
    key_activities: List[str]
    user_behavior_patterns: List[str]
    time_range_covered: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'workflow_patterns': self.workflow_patterns,
            'tools_used': self.tools_used,
            'previous_recommendations': self.previous_recommendations,
            'key_activities': self.key_activities,
            'user_behavior_patterns': self.user_behavior_patterns,
            'time_range_covered': self.time_range_covered
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextSummary':
        return cls(
            workflow_patterns=data.get('workflow_patterns', []),
            tools_used=data.get('tools_used', []),
            previous_recommendations=data.get('previous_recommendations', []),
            key_activities=data.get('key_activities', []),
            user_behavior_patterns=data.get('user_behavior_patterns', []),
            time_range_covered=data.get('time_range_covered', '')
        )


class ContextManager:
    """Manages rolling context summaries and recommendation deduplication."""

    def __init__(self, db_manager: DatabaseManager, max_context_windows: int = 3):
        self.db_manager = db_manager
        self.max_context_windows = max_context_windows

    def build_context_for_window(self, session_id: str, window_number: int,
                                current_window: ProcessingWindow) -> str:
        """Build comprehensive context for processing a specific window."""

        # Get previous context summaries
        previous_summaries = self._get_previous_summaries(session_id, window_number)

        # Extract current window information
        current_context = self._extract_window_context(current_window)

        # Build the context prompt
        context_prompt = self._build_context_prompt(
            previous_summaries, current_context, window_number
        )

        return context_prompt

    def _get_previous_summaries(self, session_id: str, window_number: int) -> List[ContextSummary]:
        """Get previous context summaries within the rolling window."""
        summaries = []

        # Look back up to max_context_windows
        start_window = max(1, window_number - self.max_context_windows)

        for prev_window_num in range(start_window, window_number):
            context_data = self.db_manager.get_context_summary(session_id, prev_window_num)
            if context_data:
                summary = ContextSummary.from_dict(context_data['summary_data'])
                summaries.append(summary)

        return summaries

    def _extract_window_context(self, window: ProcessingWindow) -> Dict[str, Any]:
        """Extract key contextual information from the current window."""
        if not window.frame_descriptions:
            return {
                'applications': [],
                'user_actions': [],
                'ui_elements': [],
                'workflow_description': "No activity in this window"
            }

        # Collect unique applications, actions, and UI elements
        applications = set()
        user_actions = set()
        ui_elements = set()
        workflow_steps = []

        for frame in window.frame_descriptions:
            applications.update(frame.applications)
            user_actions.update(frame.user_actions)
            ui_elements.update(frame.ui_elements)

            # Extract workflow steps from forensic descriptions
            if frame.forensic_description:
                # Look for key action indicators
                desc = frame.forensic_description.lower()
                if any(keyword in desc for keyword in ['click', 'type', 'select', 'navigate', 'open']):
                    workflow_steps.append(frame.forensic_description[:150])

        # Generate workflow description
        workflow_description = self._generate_workflow_description(
            list(applications), list(user_actions), workflow_steps
        )

        return {
            'applications': list(applications),
            'user_actions': list(user_actions),
            'ui_elements': list(ui_elements),
            'workflow_description': workflow_description,
            'time_range': f"{window.start_time:.1f}s - {window.end_time:.1f}s"
        }

    def _generate_workflow_description(self, applications: List[str],
                                     user_actions: List[str],
                                     workflow_steps: List[str]) -> str:
        """Generate a concise workflow description."""
        if not applications and not user_actions:
            return "No significant activity detected"

        description_parts = []

        if applications:
            apps_str = ", ".join(applications[:3])
            if len(applications) > 3:
                apps_str += f" (and {len(applications) - 3} others)"
            description_parts.append(f"User working in {apps_str}")

        if workflow_steps:
            # Use the most informative workflow step
            key_step = max(workflow_steps, key=len) if workflow_steps else ""
            if key_step:
                description_parts.append(f"Key activity: {key_step}")

        return ". ".join(description_parts)

    def _build_context_prompt(self, previous_summaries: List[ContextSummary],
                             current_context: Dict[str, Any],
                             window_number: int) -> str:
        """Build the context prompt for GPT-5."""

        context_sections = []

        # Add session overview
        context_sections.append(f"**ANALYSIS CONTEXT FOR WINDOW {window_number}**")

        if previous_summaries:
            context_sections.append("\n**PREVIOUS WORKFLOW CONTEXT:**")

            # Aggregate information from previous windows
            all_tools = set()
            all_patterns = set()
            all_recommendations = set()

            for summary in previous_summaries:
                all_tools.update(summary.tools_used)
                all_patterns.update(summary.workflow_patterns)
                all_recommendations.update(summary.previous_recommendations)

            if all_tools:
                context_sections.append(f"Tools previously used: {', '.join(list(all_tools)[:10])}")

            if all_patterns:
                context_sections.append(f"Workflow patterns observed: {'; '.join(list(all_patterns)[:5])}")

            if all_recommendations:
                context_sections.append("Previous recommendations made:")
                for i, rec in enumerate(list(all_recommendations)[:5], 1):
                    context_sections.append(f"  {i}. {rec}")
                context_sections.append("\n**IMPORTANT**: Avoid repeating these recommendations unless significant new context warrants re-emphasis.")

        # Add current window context
        context_sections.append(f"\n**CURRENT WINDOW ANALYSIS ({current_context.get('time_range', 'Unknown range')}):**")
        context_sections.append(f"Applications in use: {', '.join(current_context.get('applications', ['None']))}")
        context_sections.append(f"User actions: {', '.join(current_context.get('user_actions', ['None']))}")
        context_sections.append(f"Workflow: {current_context.get('workflow_description', 'No description available')}")

        # Add analysis instructions
        context_sections.append("""
**ANALYSIS INSTRUCTIONS:**
1. Build upon the previous context without repeating already-made recommendations
2. Focus on NEW inefficiencies or optimization opportunities specific to this window
3. Consider how current activities relate to the broader workflow patterns
4. Prioritize recommendations that haven't been suggested before
5. If you identify the same issue again, provide a different solution or deeper analysis
        """)

        return "\n".join(context_sections)

    def extract_recommendations_from_analysis(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Extract structured recommendations from GPT-5 analysis text."""
        recommendations = []

        # Simple extraction based on markdown structure
        lines = analysis_text.split('\n')
        current_recommendation = None

        for line in lines:
            line = line.strip()

            # Look for recommendation headers
            if line.startswith('### Recommendation') or line.startswith('## Recommendation'):
                if current_recommendation:
                    recommendations.append(current_recommendation)

                # Extract title and score if present
                title = line.replace('### Recommendation', '').replace('## Recommendation', '').strip()
                score_match = None
                if '(Score:' in title:
                    parts = title.split('(Score:')
                    title = parts[0].strip()
                    score_text = parts[1].replace(')', '').strip()
                    try:
                        score_match = float(score_text.split('/')[0])
                    except:
                        score_match = None

                current_recommendation = {
                    'recommendation_text': title,
                    'category': self._categorize_recommendation(title),
                    'confidence_score': score_match or 0.8,
                    'implementation_steps': [],
                    'expected_impact': ''
                }

            # Look for implementation steps
            elif line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
                if current_recommendation:
                    current_recommendation['implementation_steps'].append(line)

            # Look for expected impact
            elif 'Expected Impact:' in line or 'Impact:' in line:
                if current_recommendation:
                    current_recommendation['expected_impact'] = line.split(':')[1].strip()

            # Add to recommendation text if we're in a recommendation block
            elif current_recommendation and line and not line.startswith('#'):
                if len(current_recommendation['recommendation_text']) < 500:  # Avoid very long texts
                    current_recommendation['recommendation_text'] += ' ' + line

        # Add the last recommendation
        if current_recommendation:
            recommendations.append(current_recommendation)

        # If no structured recommendations found, create a general one
        if not recommendations and analysis_text.strip():
            recommendations.append({
                'recommendation_text': analysis_text[:300] + "..." if len(analysis_text) > 300 else analysis_text,
                'category': 'general',
                'confidence_score': 0.5,
                'implementation_steps': [],
                'expected_impact': 'Workflow optimization'
            })

        return recommendations

    def _categorize_recommendation(self, text: str) -> str:
        """Categorize a recommendation based on its content."""
        text_lower = text.lower()

        if any(word in text_lower for word in ['shortcut', 'keyboard', 'hotkey']):
            return 'shortcuts'
        elif any(word in text_lower for word in ['automation', 'automate', 'script']):
            return 'automation'
        elif any(word in text_lower for word in ['organize', 'structure', 'workflow']):
            return 'organization'
        elif any(word in text_lower for word in ['tool', 'software', 'app']):
            return 'tools'
        elif any(word in text_lower for word in ['time', 'efficiency', 'faster']):
            return 'efficiency'
        else:
            return 'general'

    def save_window_context(self, session_id: str, window_number: int,
                          window_context: Dict[str, Any],
                          analysis_result: str) -> bool:
        """Save context and analysis results for a window."""

        # Extract recommendations from analysis
        recommendations = self.extract_recommendations_from_analysis(analysis_result)

        # Create context summary
        summary = ContextSummary(
            workflow_patterns=[window_context.get('workflow_description', '')],
            tools_used=window_context.get('applications', []),
            previous_recommendations=[rec['recommendation_text'] for rec in recommendations],
            key_activities=window_context.get('user_actions', []),
            user_behavior_patterns=[],
            time_range_covered=window_context.get('time_range', '')
        )

        # Save to database
        context_id = f"{session_id}_context_{window_number}"

        success = self.db_manager.save_context_summary(
            context_id=context_id,
            session_id=session_id,
            window_number=window_number,
            summary_data=summary.to_dict(),
            workflow_patterns=summary.workflow_patterns,
            tools_used=summary.tools_used,
            previous_recommendations=summary.previous_recommendations
        )

        if success:
            # Also save recommendations
            self.db_manager.save_recommendations(session_id, window_number, recommendations)
            logger.info(f"Saved context and {len(recommendations)} recommendations for window {window_number}")
        else:
            logger.error(f"Failed to save context for window {window_number}")

        return success

    def get_session_workflow_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a comprehensive workflow summary for the entire session."""

        # Get all recommendations for the session
        recommendations = self.db_manager.get_session_recommendations(session_id)

        # Get all windows for the session
        windows = self.db_manager.get_session_windows(session_id)

        # Aggregate tools and patterns
        all_tools = set()
        all_patterns = set()

        for window_num in range(1, len(windows) + 1):
            context = self.db_manager.get_context_summary(session_id, window_num)
            if context:
                all_tools.update(context.get('tools_used', []))
                all_patterns.update(context.get('workflow_patterns', []))

        # Categorize recommendations
        category_counts = {}
        for rec in recommendations:
            category = rec.get('category', 'general')
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            'total_recommendations': len(recommendations),
            'tools_identified': list(all_tools),
            'workflow_patterns': list(all_patterns),
            'recommendation_categories': category_counts,
            'processing_status': {
                'total_windows': len(windows),
                'completed_windows': len([w for w in windows if w['status'] == 'completed'])
            }
        }