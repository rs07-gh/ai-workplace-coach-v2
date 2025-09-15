"""
Basic tests for the AI Coaching Framework.
Run with: python -m pytest tests/test_framework.py -v
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.config import Config
from src.frame_processor import FrameProcessor
from src.prompt_manager import PromptManager
from src.window_manager import WindowManager
from src.utils import safe_json_parse, format_timestamp, parse_time_to_seconds

class TestFrameProcessor:
    """Test frame processing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = FrameProcessor()

        self.sample_frames = {
            "frames": [
                {"timestamp": 0.5, "description": "Opening application"},
                {"timestamp": 30.2, "description": "User typing text"},
                {"timestamp": 60.8, "description": "Saving document"}
            ]
        }

    def test_parse_frame_descriptions_basic_format(self):
        """Test parsing basic frame format."""
        frames = self.processor.parse_frame_descriptions(self.sample_frames)

        assert len(frames) == 3
        assert frames[0].timestamp == 0.5
        assert frames[0].description == "Opening application"
        assert frames[1].timestamp == 30.2
        assert frames[2].timestamp == 60.8

    def test_parse_frame_descriptions_json_string(self):
        """Test parsing from JSON string."""
        json_string = json.dumps(self.sample_frames)
        frames = self.processor.parse_frame_descriptions(json_string)

        assert len(frames) == 3
        assert frames[0].description == "Opening application"

    def test_parse_windows_format(self):
        """Test parsing windows format."""
        windows_data = {
            "windows": [
                {
                    "frames": [
                        {"timestamp": 0, "description": "Frame 1"},
                        {"timestamp": 30, "description": "Frame 2"}
                    ]
                }
            ]
        }

        frames = self.processor.parse_frame_descriptions(windows_data)
        assert len(frames) == 2
        assert frames[0].description == "Frame 1"

    def test_chunk_by_interval(self):
        """Test chunking frames into windows."""
        frames = self.processor.parse_frame_descriptions(self.sample_frames)
        windows = self.processor.chunk_by_interval(frames, 1.0)  # 1 minute intervals

        assert len(windows) == 2  # Should create 2 windows for ~60 seconds of data
        assert windows[0].frame_count == 2  # First two frames
        assert windows[1].frame_count == 1  # Last frame

    def test_validate_frame_data_valid(self):
        """Test validation of valid frame data."""
        validation = self.processor.validate_frame_data(self.sample_frames)

        assert validation['valid'] is True
        assert validation['frame_count'] == 3
        assert validation['has_timestamps'] is True
        assert validation['has_descriptions'] is True

    def test_validate_frame_data_invalid(self):
        """Test validation of invalid frame data."""
        invalid_data = {"not_frames": []}
        validation = self.processor.validate_frame_data(invalid_data)

        assert validation['valid'] is False
        assert validation['frame_count'] == 0

class TestPromptManager:
    """Test prompt management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = PromptManager()

    def test_get_default_prompts(self):
        """Test getting default prompts."""
        system_prompt = self.manager.get_default_system_prompt()
        user_prompt = self.manager.get_default_user_prompt()

        assert len(system_prompt) > 100
        assert len(user_prompt) > 50
        assert "performance coach" in system_prompt.lower()
        assert "analyze" in user_prompt.lower()

    def test_template_creation(self):
        """Test creating prompts from templates."""
        templates = self.manager.get_available_templates()

        assert 'efficiency_focused' in templates
        assert 'automation_focused' in templates

        # Test template creation
        template_prompt = self.manager.create_user_prompt_from_template('efficiency_focused')
        assert len(template_prompt) > 100
        assert 'efficiency' in template_prompt.lower()

    def test_prompt_validation(self):
        """Test prompt validation."""
        valid_prompt = "Analyze the provided frame descriptions and recommend improvements."
        validation = self.manager.validate_prompt(valid_prompt)

        assert validation['valid'] is True
        assert validation['character_count'] > 50

        # Test invalid prompt
        invalid_prompt = "Short"
        validation = self.manager.validate_prompt(invalid_prompt)
        assert validation['valid'] is False

class TestWindowManager:
    """Test window management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = WindowManager()

        # Create sample window
        from src.frame_processor import Window, Frame, WindowSummary

        frames = [
            Frame(timestamp=0.0, description="Opening app", application="Chrome"),
            Frame(timestamp=30.0, description="Typing text", application="Chrome"),
            Frame(timestamp=60.0, description="Clicking button", application="Chrome")
        ]

        summary = WindowSummary(
            frame_count=3,
            time_span="0:00 - 1:00",
            applications=["Chrome"],
            main_activities=["typing (2x)", "clicking (1x)"],
            key_descriptions=["Opening app", "Clicking button"]
        )

        self.window = Window(
            index=0,
            start_time=0.0,
            end_time=60.0,
            duration=60.0,
            frame_count=3,
            frames=frames,
            summary=summary
        )

    def test_build_context_prompt(self):
        """Test building context prompt."""
        context_prompt = self.manager.build_context_prompt(self.window)

        assert "Window 1 Analysis Context" in context_prompt
        assert "Time Range:" in context_prompt
        assert "Frame Count: 3" in context_prompt
        assert "Opening app" in context_prompt

    def test_summarize_window(self):
        """Test window summarization."""
        summary = self.manager.summarize_window(self.window, "Recommend using keyboard shortcuts")

        assert "Window 1" in summary
        assert len(summary) > 0
        assert len(summary) <= 300  # Should be truncated if too long

    def test_build_sliding_context(self):
        """Test sliding context building."""
        windows = [self.window]  # Only one window for this test
        context = self.manager.build_sliding_context(windows, 1, 3)

        # Should be empty for first window
        assert context == "" or "Previous Window" in context

class TestUtils:
    """Test utility functions."""

    def test_safe_json_parse(self):
        """Test safe JSON parsing."""
        # Valid JSON
        success, data, error = safe_json_parse('{"test": "value"}')
        assert success is True
        assert data["test"] == "value"
        assert error is None

        # Invalid JSON
        success, data, error = safe_json_parse('{"invalid": json}')
        assert success is False
        assert data is None
        assert error is not None

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        # Test seconds
        assert format_timestamp(65.0) == "1:05"
        assert format_timestamp(125.5) == "2:05"

        # Test edge cases
        assert format_timestamp(0) == "0:00"
        assert format_timestamp(59) == "0:59"

    def test_parse_time_to_seconds(self):
        """Test time parsing."""
        # Test various formats
        assert parse_time_to_seconds("1:30") == 90.0
        assert parse_time_to_seconds("2:05") == 125.0
        assert parse_time_to_seconds(65.5) == 65.5
        assert parse_time_to_seconds("invalid") == 0.0

class TestConfig:
    """Test configuration management."""

    def test_config_defaults(self):
        """Test default configuration values."""
        assert Config.DEFAULT_MODEL == 'gpt-5'
        assert Config.DEFAULT_INTERVAL_MINUTES == 2.0
        assert Config.MAX_CONTEXT_WINDOWS == 3
        assert Config.RETRY_ATTEMPTS == 3

    def test_config_to_dict(self):
        """Test configuration export."""
        config_dict = Config.to_dict()

        assert 'default_model' in config_dict
        assert 'default_interval_minutes' in config_dict
        assert config_dict['default_model'] == 'gpt-5'

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_api_key_validation(self):
        """Test API key validation."""
        # Mock the environment variable
        Config.OPENAI_API_KEY = 'test-key'
        assert Config.validate_api_key() is True

        # Test empty key
        Config.OPENAI_API_KEY = ''
        assert Config.validate_api_key() is False

# Integration test
class TestIntegration:
    """Integration tests for the complete framework."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.sample_data = {
            "frames": [
                {"timestamp": 0, "description": "Opening Chrome browser"},
                {"timestamp": 30, "description": "Navigating to Gmail"},
                {"timestamp": 60, "description": "Reading first email"},
                {"timestamp": 90, "description": "Composing reply"},
                {"timestamp": 120, "description": "Sending email"}
            ]
        }

    def test_frame_processing_pipeline(self):
        """Test complete frame processing pipeline."""
        processor = FrameProcessor()

        # Parse frames
        frames = processor.parse_frame_descriptions(self.sample_data)
        assert len(frames) == 5

        # Create windows
        windows = processor.chunk_by_interval(frames, 1.0)  # 1 minute
        assert len(windows) == 2  # Should create 2 windows

        # Test window properties
        assert windows[0].frame_count >= 2
        assert windows[0].duration == 60.0

    def test_prompt_and_window_integration(self):
        """Test integration between prompt manager and window manager."""
        processor = FrameProcessor()
        prompt_manager = PromptManager()
        window_manager = WindowManager()

        # Process frames
        frames = processor.parse_frame_descriptions(self.sample_data)
        windows = processor.chunk_by_interval(frames, 2.0)  # 2 minutes

        # Build context
        if windows:
            context_prompt = window_manager.build_context_prompt(windows[0])
            system_prompt = prompt_manager.get_system_prompt()

            assert len(context_prompt) > 100
            assert len(system_prompt) > 100
            assert "Window 1" in context_prompt

# Fixtures for pytest
@pytest.fixture
def sample_frame_data():
    """Sample frame data fixture."""
    return {
        "frames": [
            {"timestamp": 0, "description": "Test frame 1"},
            {"timestamp": 30, "description": "Test frame 2"},
            {"timestamp": 60, "description": "Test frame 3"}
        ]
    }

@pytest.fixture
def mock_api_response():
    """Mock API response fixture."""
    return {
        'content': 'Recommendation: Use keyboard shortcuts for efficiency',
        'confidence': 0.85,
        'processing_time': 1500,
        'model': 'gpt-5',
        'tokens_used': 250,
        'search_results': [],
        'tool_calls': 0
    }

if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])