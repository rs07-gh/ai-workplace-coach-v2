"""
GPT-5 client with Responses API integration and advanced tool calling.
Provides comprehensive analysis capabilities with research and optimization tools.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from loguru import logger
from openai import OpenAI
from openai.types import CompletionUsage

from .database import GPTConfig
from .enhanced_window_processor import ProcessingWindow


@dataclass
class AnalysisResult:
    content: str
    usage: Optional[CompletionUsage]
    processing_time_seconds: float
    model_used: str
    reasoning_effort: str
    verbosity: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'usage': {
                'prompt_tokens': self.usage.prompt_tokens if self.usage else 0,
                'completion_tokens': self.usage.completion_tokens if self.usage else 0,
                'total_tokens': self.usage.total_tokens if self.usage else 0,
            } if self.usage else None,
            'processing_time_seconds': self.processing_time_seconds,
            'model_used': self.model_used,
            'reasoning_effort': self.reasoning_effort,
            'verbosity': self.verbosity
        }


class GPT5Client:
    """GPT-5 client with Responses API and tool calling capabilities."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.default_tools = self._setup_default_tools()

    def _setup_default_tools(self) -> List[Dict[str, Any]]:
        """Setup default tools using Chat Completions API format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information about applications, tools, shortcuts, and optimization techniques",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "focus": {
                                "type": "string",
                                "description": "Focus area: shortcuts, features, optimization, documentation",
                                "enum": ["shortcuts", "features", "optimization", "documentation", "community_tips"]
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_workflow_pattern",
                    "description": "Analyze a specific workflow pattern for optimization opportunities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern_description": {
                                "type": "string",
                                "description": "Description of the workflow pattern"
                            },
                            "applications_involved": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of applications involved in the pattern"
                            },
                            "frequency": {
                                "type": "string",
                                "description": "How often this pattern occurs",
                                "enum": ["rare", "occasional", "frequent", "constant"]
                            }
                        },
                        "required": ["pattern_description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_recommendation",
                    "description": "Validate if a recommendation is feasible and hasn't been suggested before",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recommendation": {
                                "type": "string",
                                "description": "The recommendation to validate"
                            },
                            "context": {
                                "type": "string",
                                "description": "Context about the user's environment and previous recommendations"
                            }
                        },
                        "required": ["recommendation"]
                    }
                }
            }
        ]

    async def analyze_window_with_context(
        self,
        system_prompt: str,
        context_prompt: str,
        window_data: Dict[str, Any],
        config: GPTConfig,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> AnalysisResult:
        """Analyze a window using GPT-5 Responses API with full context."""

        start_time = time.time()

        # Prepare the user input combining context and window data
        user_input = self._prepare_window_input(context_prompt, window_data)

        if progress_callback:
            progress_callback(f"Starting analysis with GPT-5 {config.model}")

        try:
            # Use Chat Completions API for GPT-5
            result = await self._call_chat_completions_api(
                system_prompt=system_prompt,
                user_input=user_input,
                config=config,
                progress_callback=progress_callback
            )

            processing_time = time.time() - start_time

            analysis_result = AnalysisResult(
                content=result['content'],
                usage=result.get('usage'),
                processing_time_seconds=processing_time,
                model_used=config.model,
                reasoning_effort=config.reasoning_effort,
                verbosity=config.verbosity
            )

            if progress_callback:
                progress_callback(f"Analysis completed in {processing_time:.1f}s")

            return analysis_result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"GPT-5 analysis failed after {processing_time:.1f}s: {e}")

            # Return error result
            return AnalysisResult(
                content=f"Analysis failed: {str(e)}",
                usage=None,
                processing_time_seconds=processing_time,
                model_used=config.model,
                reasoning_effort=config.reasoning_effort,
                verbosity=config.verbosity
            )

    def _prepare_window_input(self, context_prompt: str, window_data: Dict[str, Any]) -> str:
        """Prepare the complete input for GPT-5 analysis."""

        input_sections = [context_prompt]

        # Add window frame descriptions
        if 'frame_descriptions' in window_data:
            input_sections.append("\n**CURRENT WINDOW FRAME DESCRIPTIONS:**")

            for i, frame in enumerate(window_data['frame_descriptions'], 1):
                input_sections.append(f"\n--- Frame {i} at {frame.get('timestamp', 'Unknown')} ---")
                input_sections.append(frame.get('forensic_description', 'No description'))

                if frame.get('applications'):
                    input_sections.append(f"Applications: {', '.join(frame['applications'])}")

                if frame.get('user_actions'):
                    input_sections.append(f"User Actions: {', '.join(frame['user_actions'])}")

        # Add specific analysis request
        input_sections.append("""
**ANALYSIS REQUEST:**
Analyze this window for workflow optimization opportunities. Use your web search and analysis tools to:

1. Research the applications being used for hidden features and shortcuts
2. Identify inefficient patterns in the user's workflow
3. Suggest specific, actionable improvements
4. Avoid repeating recommendations from the previous context
5. Provide implementation steps for each recommendation
6. Include confidence scores and expected impact

Structure your response with clear recommendations, implementation steps, and supporting research.
        """)

        return "\n".join(input_sections)

    async def _call_chat_completions_api(
        self,
        system_prompt: str,
        user_input: str,
        config: GPTConfig,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Call GPT-5 using the Chat Completions API."""

        # Build messages for Chat Completions API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        # Build request parameters for GPT-5 Chat Completions
        request_params = {
            "model": config.model,
            "messages": messages,
            "max_completion_tokens": 2000,  # GPT-5 uses max_completion_tokens instead of max_tokens
        }

        # Add GPT-5 specific parameters
        if config.model.startswith('gpt-5'):
            # reasoning_effort: minimal, low, medium (default), high
            if hasattr(config, 'reasoning_effort') and config.reasoning_effort:
                request_params["reasoning_effort"] = config.reasoning_effort

            # verbosity: low, medium (default), high - direct API parameter for GPT-5
            if hasattr(config, 'verbosity') and config.verbosity:
                request_params["verbosity"] = config.verbosity

                # Adjust max_completion_tokens based on verbosity for better responses
                verbosity_tokens = {
                    'low': 1000,
                    'medium': 2000,
                    'high': 4000
                }
                request_params["max_completion_tokens"] = verbosity_tokens.get(config.verbosity, 2000)

        # Add tools if enabled (temporarily disabled to test basic functionality)
        # if hasattr(self, 'default_tools') and self.default_tools:
        #     request_params["tools"] = self.default_tools
        #     request_params["tool_choice"] = "auto"

        if progress_callback:
            progress_callback("Sending request to GPT-5 Chat Completions API...")

        # Debug: Log the request parameters
        logger.info(f"GPT-5 API request params: {json.dumps({k: v if k != 'messages' else f'[{len(v)} messages]' for k, v in request_params.items()}, indent=2)}")

        # Make the API call using Chat Completions
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            **request_params
        )

        if progress_callback:
            progress_callback("Processing GPT-5 response...")

        # Extract content and usage information
        content = ""
        usage = None

        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
        else:
            content = str(response)

        if hasattr(response, 'usage'):
            usage = response.usage

        return {
            'content': content,
            'usage': usage,
            'raw_response': response
        }

    async def batch_analyze_windows(
        self,
        system_prompt: str,
        windows_with_context: List[Dict[str, Any]],
        config: GPTConfig,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[AnalysisResult]:
        """Analyze multiple windows in sequence with context continuity."""

        results = []
        total_windows = len(windows_with_context)

        for i, window_context in enumerate(windows_with_context, 1):
            if progress_callback:
                progress_callback(f"Processing window {i}", i, total_windows)

            try:
                result = await self.analyze_window_with_context(
                    system_prompt=system_prompt,
                    context_prompt=window_context['context'],
                    window_data=window_context['window_data'],
                    config=config,
                    progress_callback=lambda msg: progress_callback(f"Window {i}: {msg}", i, total_windows) if progress_callback else None
                )
                results.append(result)

                # Brief delay to avoid rate limits
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to analyze window {i}: {e}")
                error_result = AnalysisResult(
                    content=f"Failed to analyze window {i}: {str(e)}",
                    usage=None,
                    processing_time_seconds=0.0,
                    model_used=config.model,
                    reasoning_effort=config.reasoning_effort,
                    verbosity=config.verbosity
                )
                results.append(error_result)

        return results

    def estimate_token_usage(self, system_prompt: str, context_prompt: str,
                           window_data: Dict[str, Any]) -> Dict[str, int]:
        """Estimate token usage for a window analysis."""

        # Simple estimation based on character count
        # GPT-5 tokenizer would give more accurate results
        full_input = self._prepare_window_input(context_prompt, window_data)
        total_text = system_prompt + full_input

        # Rough estimation: ~4 characters per token
        estimated_input_tokens = len(total_text) // 4

        # Estimate output tokens based on verbosity setting
        verbosity_multipliers = {
            'minimal': 100,
            'low': 300,
            'medium': 600,
            'high': 1000
        }

        estimated_output_tokens = verbosity_multipliers.get('medium', 600)

        return {
            'estimated_input_tokens': estimated_input_tokens,
            'estimated_output_tokens': estimated_output_tokens,
            'estimated_total_tokens': estimated_input_tokens + estimated_output_tokens
        }

    def calculate_estimated_cost(self, token_estimates: Dict[str, int], model: str) -> float:
        """Calculate estimated cost based on GPT-5 pricing."""

        pricing = {
            'gpt-5': {'input': 1.25, 'output': 10.0},      # per 1M tokens
            'gpt-5-mini': {'input': 0.25, 'output': 2.0},
            'gpt-5-nano': {'input': 0.05, 'output': 0.40}
        }

        if model not in pricing:
            model = 'gpt-5'  # default

        input_cost = (token_estimates['estimated_input_tokens'] / 1_000_000) * pricing[model]['input']
        output_cost = (token_estimates['estimated_output_tokens'] / 1_000_000) * pricing[model]['output']

        return input_cost + output_cost

    async def test_connection(self, config: GPTConfig) -> Dict[str, Any]:
        """Test the connection to GPT-5 and validate configuration."""

        try:
            test_prompt = "This is a test prompt to validate GPT-5 configuration."

            start_time = time.time()
            result = await self._call_chat_completions_api(
                system_prompt="You are a test assistant. Respond with 'Configuration test successful' and nothing else.",
                user_input=test_prompt,
                config=config
            )
            end_time = time.time()

            return {
                'success': True,
                'response_time': end_time - start_time,
                'model': config.model,
                'content': result['content'],
                'usage': result.get('usage')
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'model': config.model
            }