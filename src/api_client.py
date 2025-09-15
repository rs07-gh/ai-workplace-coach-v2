"""
OpenAI API Client with GPT-5 integration and web search tools.
Handles API calls, retries, and tool usage for research-enhanced coaching recommendations.
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any, Union
from openai import OpenAI, AsyncOpenAI
from .config import Config
from .utils import setup_logging

logger = setup_logging(__name__)

class APIClient:
    """OpenAI API client with GPT-5 and tool support."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize API client."""
        self.api_key = api_key or Config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.async_client = AsyncOpenAI(api_key=self.api_key)

        # API settings
        self.base_url = 'https://api.openai.com/v1'
        self.timeout = Config.TIMEOUT_MS / 1000  # Convert to seconds
        self.max_retries = Config.RETRY_ATTEMPTS
        self.retry_delay = 2.0

    def generate_recommendation(
        self,
        system_prompt: str,
        user_prompt: str,
        frame_context: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate coaching recommendation using GPT-5 with tools.

        Args:
            system_prompt: System prompt defining AI role
            user_prompt: User instructions for analysis
            frame_context: Frame descriptions and context
            settings: Optional API settings override

        Returns:
            Dictionary with recommendation content and metadata
        """
        start_time = time.time()

        # Merge settings
        api_settings = Config.get_api_settings()
        if settings:
            api_settings.update(settings)

        # Ensure we're using GPT-5 for complex coaching analysis
        model_name = api_settings.get('model_name', 'gpt-5')
        if 'nano' in model_name:
            logger.warning(f"Switching from {model_name} to gpt-5 for coaching analysis")
            model_name = 'gpt-5'

        # Build complete user input
        user_input = self._build_user_input(system_prompt, user_prompt, frame_context)

        try:
            if model_name.startswith('gpt-5'):
                # Use GPT-5 Responses API with tools
                return self._call_gpt5_responses_api(user_input, api_settings, start_time)
            else:
                # Use Chat Completions API for other models
                return self._call_chat_completion(user_input, api_settings, start_time)

        except Exception as error:
            logger.error(f"API call failed: {error}")
            raise error

    def _call_gpt5_responses_api(
        self,
        user_input: str,
        settings: Dict[str, Any],
        start_time: float
    ) -> Dict[str, Any]:
        """Call GPT-5 using the Responses API with proper format and parameters."""

        # GPT-5 uses Responses API with specific format
        payload = {
            "model": settings.get('model_name', 'gpt-5'),
            "input": user_input  # String input, not messages array
        }

        # Add GPT-5 specific parameters with proper nesting
        reasoning_effort = settings.get('reasoning_effort', 'medium')
        valid_efforts = ['minimal', 'low', 'medium', 'high']
        if reasoning_effort not in valid_efforts:
            reasoning_effort = 'medium'

        # Properly nested GPT-5 parameters
        payload['reasoning'] = {'effort': reasoning_effort}

        # Add verbosity parameter with proper nesting
        verbosity = settings.get('verbosity', 'medium')
        payload['text'] = {'verbosity': verbosity}

        # Add web search tools for parallel workflow support
        payload['tools'] = self._get_web_search_tools()

        # Enable parallel tool calls as required by system prompt
        payload['parallel_tool_calls'] = True

        # Add max tokens with correct GPT-5 parameter name
        if settings.get('max_tokens'):
            payload['max_output_tokens'] = settings['max_tokens']

        # Note: temperature is NOT supported by GPT-5 - removed

        response = self._make_api_call_with_retry(payload, use_responses_api=True)
        return self._parse_gpt5_response(response, start_time, settings)

    def _call_chat_completion(
        self,
        user_input: str,
        settings: Dict[str, Any],
        start_time: float
    ) -> Dict[str, Any]:
        """Call Chat Completions API for non-GPT-5 models."""

        payload = {
            "model": settings.get('model_name', 'gpt-4'),
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        }

        if settings.get('max_tokens'):
            payload['max_tokens'] = settings['max_tokens']
        # Note: temperature parameter removed - not consistent across all models

        response = self._make_api_call_with_retry(payload, use_tools=False)
        return self._parse_chat_response(response, start_time, settings)

    def _make_api_call_with_retry(
        self,
        payload: Dict[str, Any],
        use_tools: bool = False,
        use_responses_api: bool = False
    ) -> Dict[str, Any]:
        """Make API call with retry logic."""

        attempt = 1
        while attempt <= self.max_retries:
            try:
                logger.info(f"API call attempt {attempt} (model: {payload.get('model', 'unknown')})")

                if use_responses_api:
                    # Use GPT-5 Responses API
                    response = self.client.responses.create(**payload)
                    return response.model_dump()
                else:
                    # Use Chat Completions API for non-GPT-5 models
                    response = self.client.chat.completions.create(**payload)
                    return response.model_dump()

            except Exception as error:
                if attempt < self.max_retries:
                    delay = self.retry_delay * attempt
                    logger.warning(f"API call failed (attempt {attempt}), retrying in {delay}s: {error}")
                    time.sleep(delay)
                    attempt += 1
                    continue
                else:
                    logger.error(f"API call failed after {self.max_retries} attempts: {error}")
                    raise error

    def _parse_gpt5_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse GPT-5 response with tool calls."""

        processing_time = int((time.time() - start_time) * 1000)

        # Extract message content
        message = response.get('choices', [{}])[0].get('message', {})
        content = message.get('content', '') or ''
        tool_calls = message.get('tool_calls', [])

        # Handle tool calls (web searches)
        search_results = []
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.get('function', {}).get('name') == 'web_search':
                    # In a real implementation, you would execute the web search
                    # For now, we'll simulate it
                    args = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
                    search_results.append({
                        'query': args.get('query', ''),
                        'focus': args.get('focus', 'general'),
                        'simulated': True
                    })

        # Extract usage information
        usage = response.get('usage', {})
        tokens_used = usage.get('total_tokens', 0)

        # Extract reasoning if available
        reasoning = response.get('reasoning', '') or ''

        # Parse recommendations
        recommendations = self._extract_recommendations(content)
        confidence = self._extract_confidence(reasoning or content)

        return {
            'content': content,
            'recommendations': recommendations,
            'reasoning': reasoning,
            'confidence': confidence,
            'processing_time': processing_time,
            'model': settings.get('model_name', 'gpt-5'),
            'reasoning_effort': settings.get('reasoning_effort', 'medium'),
            'verbosity': settings.get('verbosity', 'medium'),
            'tokens_used': tokens_used,
            'search_results': search_results,
            'tool_calls': len(tool_calls),
            'raw_response': response
        }

    def _parse_chat_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse standard chat completion response."""

        processing_time = int((time.time() - start_time) * 1000)

        # Extract content
        content = response.get('choices', [{}])[0].get('message', {}).get('content', '') or ''

        # Extract usage
        usage = response.get('usage', {})
        tokens_used = usage.get('total_tokens', 0)

        # Parse recommendations
        recommendations = self._extract_recommendations(content)
        confidence = self._extract_confidence(content)

        return {
            'content': content,
            'recommendations': recommendations,
            'reasoning': '',
            'confidence': confidence,
            'processing_time': processing_time,
            'model': settings.get('model_name', 'gpt-4'),
            'tokens_used': tokens_used,
            'search_results': [],
            'tool_calls': 0,
            'raw_response': response
        }

    def _build_user_input(
        self,
        system_prompt: str,
        user_prompt: str,
        frame_context: str
    ) -> str:
        """Build complete user input combining prompts and context."""

        return f"""{system_prompt}

## User Instructions
{user_prompt}

## Frame Analysis Context
{frame_context}

Please analyze this context and provide specific, actionable productivity recommendations following the guidelines above. Use web search tools proactively to research applications and validate optimization techniques."""

    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract individual recommendations from response content."""

        if not content:
            return []

        recommendations = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            # Look for numbered lists, bullet points, or explicit recommendations
            if any([
                line.startswith(tuple(f'{i}.' for i in range(1, 11))),
                line.startswith(('•', '-', '*')),
                line.startswith('[') and ']:' in line,
                'recommendation' in line.lower() and ':' in line
            ]):
                recommendations.append(line)

        # If no structured recommendations found, use paragraphs
        if not recommendations and content:
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if len(para) > 50:  # Substantial content
                    recommendations.append(para[:500] + ('...' if len(para) > 500 else ''))

        return recommendations[:5]  # Limit to top 5

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence score from reasoning or content."""

        if not text:
            return 0.8

        import re

        # Look for explicit confidence mentions
        confidence_match = re.search(r'confidence[:\s]*([0-9]+(?:\.[0-9]+)?)', text.lower())
        if confidence_match:
            score = float(confidence_match.group(1))
            return score if score <= 1.0 else score / 100.0

        # Infer from language
        text_lower = text.lower()
        if any(word in text_lower for word in ['highly confident', 'certain', 'definite']):
            return 0.9
        elif any(word in text_lower for word in ['confident', 'likely', 'probable']):
            return 0.8
        elif any(word in text_lower for word in ['possible', 'might', 'could']):
            return 0.6
        elif any(word in text_lower for word in ['uncertain', 'unsure', 'unclear']):
            return 0.5

        return 0.75  # Default confidence

    def _get_web_search_tools(self) -> List[Dict[str, Any]]:
        """Get web search tool definitions for GPT-5."""

        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for current information about applications, tools, shortcuts, best practices, and optimization techniques. Use this proactively to validate and enhance recommendations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query. Be specific about the application/tool and what you're looking for (e.g., 'Excel keyboard shortcuts 2024', 'Chrome DevTools productivity tips')"
                            },
                            "focus": {
                                "type": "string",
                                "enum": ["general", "documentation", "tutorials", "shortcuts", "best_practices", "community_tips"],
                                "description": "What type of information to focus on",
                                "default": "general"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def test_connection(self, test_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Test API connectivity and configuration."""

        try:
            settings = Config.get_api_settings()
            if test_settings:
                settings.update(test_settings)

            logger.info(f"Testing API connection with model: {settings.get('model_name')}")

            result = self.generate_recommendation(
                system_prompt="You are a test assistant. Respond concisely.",
                user_prompt='Respond with exactly "Connection successful" and nothing else.',
                frame_context="Simple test for API connectivity",
                settings=settings
            )

            return {
                'success': True,
                'message': f"{settings.get('model_name')} API connection successful",
                'model': result['model'],
                'processing_time': result['processing_time'],
                'tokens_used': result['tokens_used'],
                'response_content': result['content'][:100]
            }

        except Exception as error:
            logger.error(f"API connection test failed: {error}")
            return {
                'success': False,
                'message': str(error),
                'error': error.__class__.__name__
            }