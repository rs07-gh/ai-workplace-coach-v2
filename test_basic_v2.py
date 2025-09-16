#!/usr/bin/env python3
"""
Basic test script for AI Coaching Framework v2
Tests core functionality without external dependencies.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")

    try:
        # Add src to path for imports
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)

        from database import DatabaseManager, GPTConfig, ProcessingConfig
        from enhanced_window_processor import EnhancedWindowProcessor
        from context_manager import ContextManager
        from gpt5_client import GPT5Client
        from batch_processor import BatchProcessor
        print("  ✅ All imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    print("\n🧪 Testing file structure...")

    required_files = [
        "src/database.py",
        "src/enhanced_window_processor.py",
        "src/context_manager.py",
        "src/gpt5_client.py",
        "src/batch_processor.py",
        "src/prompts/klarity_coach_system_prompt.md",
        "app_v2.py",
        "requirements.txt"
    ]

    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"  ❌ {file_path}")

    if missing_files:
        print(f"  Missing files: {missing_files}")
        return False

    print("  ✅ All required files present")
    return True

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\n🧪 Testing basic functionality...")

    try:
        # Add src to path
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)

        from database import DatabaseManager, GPTConfig, ProcessingConfig
        from enhanced_window_processor import EnhancedWindowProcessor

        # Test basic class instantiation
        db_path = "test_basic.db"
        if os.path.exists(db_path):
            os.remove(db_path)

        db_manager = DatabaseManager(db_path)
        processor = EnhancedWindowProcessor(window_seconds=30)

        print("  ✅ Class instantiation successful")

        # Test configuration objects
        gpt_config = GPTConfig(model="gpt-5-mini")
        processing_config = ProcessingConfig(window_seconds=30)

        print("  ✅ Configuration objects created")

        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)

        return True

    except Exception as e:
        print(f"  ❌ Basic functionality test failed: {e}")
        return False

def test_json_structure():
    """Test JSON validation functionality."""
    print("\n🧪 Testing JSON validation...")

    try:
        # Add src to path
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)

        from enhanced_window_processor import EnhancedWindowProcessor

        # Create test JSON
        test_data = {
            "video": "test.mp4",
            "duration_seconds": 120.0,
            "fps": 1,
            "window_seconds": 30,
            "model": "gpt-5-mini",
            "processing_method": "test",
            "windows": [
                {
                    "window_analysis": {
                        "window": "1/4",
                        "time_range": "0.0s-30.0s"
                    },
                    "frame_descriptions": [
                        {
                            "timestamp": "00:00:00",
                            "forensic_description": "User opens application",
                            "applications": ["Test App"],
                            "ui_elements": ["button"],
                            "user_actions": ["click"]
                        }
                    ]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            processor = EnhancedWindowProcessor()
            is_valid, message = processor.validate_json_structure(temp_file)

            if is_valid:
                print("  ✅ JSON validation successful")
                return True
            else:
                print(f"  ❌ JSON validation failed: {message}")
                return False

        finally:
            os.remove(temp_file)

    except Exception as e:
        print(f"  ❌ JSON validation test failed: {e}")
        return False

def test_system_prompt():
    """Test system prompt loading."""
    print("\n🧪 Testing system prompt...")

    prompt_file = Path("src/prompts/klarity_coach_system_prompt.md")

    if prompt_file.exists():
        try:
            content = prompt_file.read_text(encoding='utf-8')
            if len(content) > 100 and "Klarity Coach" in content:
                print("  ✅ System prompt loaded successfully")
                return True
            else:
                print("  ❌ System prompt content invalid")
                return False
        except Exception as e:
            print(f"  ❌ System prompt loading failed: {e}")
            return False
    else:
        print("  ❌ System prompt file not found")
        return False

def main():
    """Run all basic tests."""
    print("🚀 AI Coaching Framework v2 - Basic System Tests")
    print("=" * 60)

    tests = [
        test_file_structure,
        test_imports,
        test_system_prompt,
        test_basic_functionality,
        test_json_structure
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with exception: {e}")

    print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All basic tests passed! v2 framework is ready for testing.")
        print("\n🚀 Next steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run: streamlit run app_v2.py")
        print("4. Test with sample JSON files from ../04_Outputs/Step_1/")
        return True
    else:
        print(f"\n❌ {total_tests - passed_tests} tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)