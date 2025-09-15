"""
Prompt Manager - System and user prompt storage with templates.
Manages different coaching focus areas and prompt customization.
"""

import logging
from typing import Dict, List, Optional, Any
from .utils import setup_logging
from .config import Config

logger = setup_logging(__name__)

class PromptManager:
    """Manages system and user prompts with template support."""

    def __init__(self):
        self.logger = logger
        self._system_prompt = None
        self._user_prompt = None

    def get_system_prompt(self) -> str:
        """Get the system prompt for coaching analysis."""
        if self._system_prompt:
            return self._system_prompt
        return self.get_default_system_prompt()

    def get_user_prompt(self) -> str:
        """Get the user prompt for analysis instructions."""
        if self._user_prompt:
            return self._user_prompt
        return self.get_default_user_prompt()

    def set_system_prompt(self, prompt: str) -> None:
        """Set custom system prompt."""
        self._system_prompt = prompt

    def set_user_prompt(self, prompt: str) -> None:
        """Set custom user prompt."""
        self._user_prompt = prompt

    def get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return '''You are an AI Performance Coach with advanced analytical capabilities and proactive research skills, specializing in evidence-based workflow optimization. You analyze rolling windows of frame descriptions (with summary carryover) and generate asynchronous recommendations without losing context.

## Role & Operating Modes

- Primary role: Identify inefficiencies (opportunities) and commendable actions (what to keep doing) from on-screen evidence, then deliver research-validated, testable recommendations.
- Architecture alignment:
  - Input arrives as sliding/rolling window of frame descriptions with a brief previousContext summary. Maintain continuity across windows.
  - Run two parallel scans per window:
    1) Opportunities scan (inefficiencies, optimizations)
    2) Commendations scan (notable actions worth reinforcing)
  - Produce lossless coverage: do not trade off one category for the other.
- Agentic tools (GPT-5):
  - If tools are available, proactively use web search / browse to validate features, shortcuts, and best practices; use calculator/code utilities for quick math or transformations.
  - Parallelize: kick off research while you continue the frame scan.
  - If tools are unavailable, do not fabricate sources. Mark citations as TOOLING-UNAVAILABLE and proceed with conservative, widely accepted techniques.

## Core Competencies

**Analytical Framework**
Form testable hypotheses about user behavior patterns; self-critique recommendations; ground insights in observable screen evidence with precise timestamps.

**Systematic Investigation**
Read frame descriptions chronologically; interpret actions through multiple lenses (efficiency, accuracy, tool mastery); detect both obvious inefficiencies and subtle improvements.

**Proactive Research Excellence**
For every application/tool observed, launch parallel web searches for official docs, shortcuts, community techniques, hidden features. Cross-check recency and credibility.

**Hypothesis Development**
Generate multiple competing theories, enhance with research findings, test each against on-screen evidence, critique assumptions, then synthesize the best-supported recommendation.

**Evidence Standards**
Every claim must reference specific timestamps, measurable patterns, and (when tools are available) authoritative sources.

## Enhanced Platform Eligibility Gate (PEG)

WellKnown Platforms — ALLOW:
- Operating Systems: Windows, macOS, Linux (built-in features)
- Standard Applications: Microsoft Office, Google Workspace, Chrome/Firefox/Safari
- Popular Business Tools: Slack, Zoom, Jira, Confluence, Asana, Trello, GitHub, GitLab, Notion, Airtable
- Enterprise Platforms: Salesforce, HubSpot, Zendesk, ServiceNow, SAP, Oracle ERP Cloud, Workday
- Development Tools: VS Code, common editors, CLI tools
- Personal Productivity: Note-taking apps, file managers, standard utilities

InternalOrUnknown Platforms — EVALUATE:
- Custom enterprise software and portals; industry-specific tools; bespoke CRMs and consoles; niche extensions

## Quality & Safety Checklist

- Each opportunity cites specific timestamps from this window.
- Claimed features are validated (tools available) or labeled TOOLING-UNAVAILABLE.
- Implementation steps are solo-executable (no IT tickets unless explicitly allowed).
- Commendations are present when warranted.

## Success Criteria

- Research Integration with credible sources
- Source Quality and recency
- Hypothesis Enhancement via research
- Evidence Grounding with timestamps
- Implementation Clarity for same-day action
- Measurable Impact (≥2 minutes saved per occurrence or clear quality/risk reduction)
- Innovation Discovery: surface lesser-known but robust techniques

Analysis Target: Provide evidence-based, research-enhanced, hypothesis-driven optimization that respects the PEG gate and achieves high constraint scores—without losing commendable actions.'''

    def get_default_user_prompt(self) -> str:
        """Get the default user prompt."""
        return '''Analyze the provided frame descriptions and generate specific, actionable productivity recommendations.

Focus on:
1. Observable inefficiencies with timestamp evidence
2. Opportunities for keyboard shortcuts or automation
3. Tool optimization based on web research
4. Personal productivity improvements using existing tools

Requirements:
- Reference specific timestamps from the frame data
- Provide concrete implementation steps
- Estimate time savings or efficiency gains
- Focus on immediately actionable changes

Format: One clear recommendation per response with implementation steps.'''

    def create_user_prompt_from_template(
        self,
        template_type: str,
        customizations: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create user prompt from template.

        Args:
            template_type: Type of template to use
            customizations: Optional customizations to apply

        Returns:
            Generated user prompt string
        """
        try:
            templates = {
                'efficiency_focused': self._get_efficiency_template(),
                'automation_focused': self._get_automation_template(),
                'learning_focused': self._get_learning_template(),
                'meeting_focused': self._get_meeting_template(),
                'coding_focused': self._get_coding_template(),
            }

            template = templates.get(template_type, self.get_default_user_prompt())

            # Apply customizations
            if customizations:
                if customizations.get('focus_area'):
                    template += f"\n\nSpecial Focus: {customizations['focus_area']}"

                if customizations.get('exclude_area'):
                    template += f"\n\nExclude: {customizations['exclude_area']}"

                if customizations.get('time_constraint'):
                    template += f"\n\nTime Constraint: Focus on changes that take {customizations['time_constraint']} or less to implement."

            self.logger.info(f"Created {template_type} user prompt: {len(template)} characters")
            return template

        except Exception as error:
            self.logger.error(f"Template creation error: {error}")
            return self.get_default_user_prompt()

    def _get_efficiency_template(self) -> str:
        """Get efficiency-focused template."""
        return '''Analyze the frame descriptions with a laser focus on efficiency improvements.

Priority Analysis Areas:
1. Time waste identification - look for delays, waiting, or redundant actions
2. Click reduction opportunities - find multi-click tasks that could be shortcuts
3. Context switching costs - identify app/tab switching that could be minimized
4. Repetitive action patterns - spot tasks suitable for automation or batching

Evidence Requirements:
- Cite exact timestamps for inefficient moments
- Quantify wasted time (e.g., "3.2 seconds spent navigating could be saved")
- Count unnecessary clicks or keystrokes
- Measure context switching frequency

Output: One high-impact efficiency recommendation with measurable time savings.'''

    def _get_automation_template(self) -> str:
        """Get automation-focused template."""
        return '''Analyze the frame descriptions specifically for automation opportunities.

Automation Scan Focus:
1. Repetitive sequences - identify patterns repeated 3+ times
2. Manual data entry - spot opportunities for auto-fill, templates, or scripts
3. File management - look for repetitive copying, moving, or organizing
4. Cross-application workflows - identify tasks spanning multiple apps

Implementation Priority:
- Built-in app features first (keyboard shortcuts, auto-features)
- Browser extensions and plugins second
- Simple scripts or macros third
- Complex automation tools last

Output: One specific automation recommendation with setup instructions and estimated setup time vs. ongoing savings.'''

    def _get_learning_template(self) -> str:
        """Get learning-focused template."""
        return '''Analyze the frame descriptions to identify learning and skill development opportunities.

Learning Assessment Areas:
1. Tool underutilization - features the user isn't leveraging
2. Workflow knowledge gaps - inefficient approaches that suggest learning needs
3. Best practice opportunities - industry-standard approaches not being used
4. Advanced feature discovery - powerful capabilities being overlooked

Research Requirements:
- Identify specific features or techniques the user should learn
- Find official documentation, tutorials, or training resources
- Assess the learning curve vs. productivity benefit
- Suggest progressive learning paths

Output: One skill/knowledge recommendation with specific learning resources and practice suggestions.'''

    def _get_meeting_template(self) -> str:
        """Get meeting-focused template."""
        return '''Analyze the frame descriptions with focus on meeting and communication productivity.

Meeting Efficiency Areas:
1. Preparation optimization - pre-meeting setup and material gathering
2. During-meeting effectiveness - note-taking, screen sharing, participation
3. Follow-up efficiency - action item capture and distribution
4. Communication tool usage - optimal use of video, chat, and collaboration features

Analysis Focus:
- Screen sharing setup and transitions
- Note-taking methods and tools
- Multitasking effectiveness during calls
- Tool switching for meeting functions

Output: One meeting productivity recommendation with specific technique or tool improvement.'''

    def _get_coding_template(self) -> str:
        """Get coding-focused template."""
        return '''Analyze the frame descriptions for software development productivity improvements.

Development Workflow Analysis:
1. IDE efficiency - shortcuts, plugins, and features underused
2. Debugging approach - time spent in debugging vs. coding
3. Testing workflow - test running, result analysis, and iteration
4. Documentation and research - efficiency of looking up information

Code Productivity Factors:
- Keyboard vs. mouse usage ratio
- Time spent in different IDE panels/windows
- Copy-paste patterns suggesting refactoring opportunities
- Error resolution approaches

Output: One development productivity recommendation with specific IDE feature or workflow improvement.'''

    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validate prompt content and structure.

        Returns:
            Dictionary with validation results
        """
        try:
            errors = []

            if not prompt or not isinstance(prompt, str):
                errors.append("Prompt must be a non-empty string")
                return {'valid': False, 'errors': errors}

            trimmed = prompt.strip()

            if len(trimmed) == 0:
                errors.append("Prompt cannot be empty or only whitespace")

            if len(trimmed) < 50:
                errors.append("Prompt should be at least 50 characters for effectiveness")

            if len(trimmed) > 8000:
                errors.append("Prompt is too long (max 8000 characters recommended)")

            # Check for analysis keywords
            analysis_keywords = ['analyze', 'recommend', 'identify', 'examine', 'assess']
            if not any(keyword in trimmed.lower() for keyword in analysis_keywords):
                errors.append("Prompt should include analysis or recommendation instructions")

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'character_count': len(trimmed),
                'word_count': len(trimmed.split()),
                'has_analysis_focus': any(keyword in trimmed.lower() for keyword in analysis_keywords)
            }

        except Exception as error:
            self.logger.error(f"Prompt validation error: {error}")
            return {
                'valid': False,
                'errors': [f'Validation failed: {error}']
            }

    def get_available_templates(self) -> Dict[str, str]:
        """Get list of available prompt templates with descriptions."""
        return {
            'efficiency_focused': 'Focuses on time waste elimination and speed improvements',
            'automation_focused': 'Identifies repetitive tasks suitable for automation',
            'learning_focused': 'Suggests skills and knowledge to develop',
            'meeting_focused': 'Optimizes video calls and collaborative work',
            'coding_focused': 'Improves software development workflows'
        }

    def export_prompts(self) -> Dict[str, str]:
        """Export current prompts as dictionary."""
        return {
            'system_prompt': self.get_system_prompt(),
            'user_prompt': self.get_user_prompt()
        }

    def import_prompts(self, prompts: Dict[str, str]) -> None:
        """Import prompts from dictionary."""
        if 'system_prompt' in prompts:
            self.set_system_prompt(prompts['system_prompt'])

        if 'user_prompt' in prompts:
            self.set_user_prompt(prompts['user_prompt'])