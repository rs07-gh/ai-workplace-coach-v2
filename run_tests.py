#!/usr/bin/env python3
"""
Test runner for the AI Coaching Framework.
Runs basic functionality tests without requiring API keys.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.frame_processor import FrameProcessor
from src.prompt_manager import PromptManager
from src.window_manager import WindowManager
from src.utils import safe_json_parse, format_timestamp
from src.config import Config

def test_frame_processing():
    """Test frame processing functionality."""
    print("🔍 Testing frame processing...")

    # Load sample data
    sample_file = Path(__file__).parent / "examples" / "sample_frames.json"

    if not sample_file.exists():
        print("❌ Sample data file not found")
        return False

    with open(sample_file, 'r') as f:
        frame_data = f.read()

    processor = FrameProcessor()

    try:
        # Parse frames
        frames = processor.parse_frame_descriptions(frame_data)
        print(f"   ✅ Parsed {len(frames)} frames")

        # Create windows
        windows = processor.chunk_by_interval(frames, 2.0)  # 2 minute intervals
        print(f"   ✅ Created {len(windows)} windows")

        # Validate
        validation = processor.validate_frame_data(frame_data)
        print(f"   ✅ Validation: {validation['valid']}")

        return True

    except Exception as e:
        print(f"   ❌ Frame processing failed: {e}")
        return False

def test_prompt_management():
    """Test prompt management functionality."""
    print("📝 Testing prompt management...")

    try:
        manager = PromptManager()

        # Test default prompts
        system_prompt = manager.get_system_prompt()
        user_prompt = manager.get_user_prompt()

        print(f"   ✅ System prompt: {len(system_prompt)} characters")
        print(f"   ✅ User prompt: {len(user_prompt)} characters")

        # Test templates
        templates = manager.get_available_templates()
        print(f"   ✅ Available templates: {len(templates)}")

        # Test template creation
        efficiency_prompt = manager.create_user_prompt_from_template('efficiency_focused')
        print(f"   ✅ Efficiency template: {len(efficiency_prompt)} characters")

        return True

    except Exception as e:
        print(f"   ❌ Prompt management failed: {e}")
        return False

def test_window_management():
    """Test window management functionality."""
    print("🪟 Testing window management...")

    try:
        # Create sample frames and windows
        from src.frame_processor import Frame, Window, WindowSummary

        frames = [
            Frame(timestamp=0.0, description="Opening application", application="Chrome"),
            Frame(timestamp=30.0, description="Navigating to website", application="Chrome"),
            Frame(timestamp=60.0, description="Filling form", application="Chrome")
        ]

        summary = WindowSummary(
            frame_count=3,
            time_span="0:00 - 1:00",
            applications=["Chrome"],
            main_activities=["navigating", "typing"],
            key_descriptions=["Opening application", "Filling form"]
        )

        window = Window(
            index=0,
            start_time=0.0,
            end_time=60.0,
            duration=60.0,
            frame_count=3,
            frames=frames,
            summary=summary
        )

        manager = WindowManager()

        # Test context building
        context_prompt = manager.build_context_prompt(window)
        print(f"   ✅ Context prompt: {len(context_prompt)} characters")

        # Test summarization
        window_summary = manager.summarize_window(window, "Test recommendation")
        print(f"   ✅ Window summary: {len(window_summary)} characters")

        return True

    except Exception as e:
        print(f"   ❌ Window management failed: {e}")
        return False

def test_utilities():
    """Test utility functions."""
    print("🔧 Testing utilities...")

    try:
        # Test JSON parsing
        success, data, error = safe_json_parse('{"test": "value"}')
        assert success and data["test"] == "value"
        print("   ✅ JSON parsing works")

        # Test timestamp formatting
        assert format_timestamp(65.0) == "1:05"
        assert format_timestamp(3665) == "61:05"  # Over an hour
        print("   ✅ Timestamp formatting works")

        return True

    except Exception as e:
        print(f"   ❌ Utilities failed: {e}")
        return False

def test_configuration():
    """Test configuration management."""
    print("⚙️  Testing configuration...")

    try:
        # Test config access
        config_dict = Config.to_dict()
        print(f"   ✅ Configuration exported: {len(config_dict)} settings")

        # Test essential settings
        assert Config.DEFAULT_MODEL == 'gpt-5'
        assert Config.DEFAULT_INTERVAL_MINUTES == 2.0
        print("   ✅ Default values correct")

        return True

    except Exception as e:
        print(f"   ❌ Configuration failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 AI Coaching Framework - Test Suite")
    print("=" * 50)

    tests = [
        test_frame_processing,
        test_prompt_management,
        test_window_management,
        test_utilities,
        test_configuration
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All tests passed! Framework is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())