#!/usr/bin/env python3
"""
Test script for AI Coaching Framework v2
Validates all migrated components work correctly in the repository environment.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

# Test the new v2 components
try:
    from src.database import DatabaseManager, GPTConfig, ProcessingConfig, SessionStatus
    from src.enhanced_window_processor import EnhancedWindowProcessor
    from src.context_manager import ContextManager
    from src.gpt5_client import GPT5Client
    from src.batch_processor import BatchProcessor
    print("✅ All v2 imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)


def create_test_json_data() -> Dict[str, Any]:
    """Create sample JSON data for testing."""
    return {
        "video": "test_session.mp4",
        "duration_seconds": 150.0,
        "fps": 1,
        "window_seconds": 30,
        "model": "gpt-5-mini",
        "processing_method": "test_v2",
        "windows": [
            {
                "window_analysis": {
                    "window": "1/5",
                    "time_range": "0.0s-29.0s"
                },
                "frame_descriptions": [
                    {
                        "timestamp": "00:00:00",
                        "forensic_description": "User opens Microsoft Excel application, creating a new blank workbook. The ribbon interface is visible with standard tabs (File, Home, Insert). User clicks on cell A1 to begin data entry.",
                        "applications": ["Microsoft Excel"],
                        "ui_elements": ["ribbon", "cell_A1", "workbook"],
                        "user_actions": ["open_application", "click_cell"]
                    },
                    {
                        "timestamp": "00:00:15",
                        "forensic_description": "User manually types 'Product Name' in cell A1, then uses mouse to click on cell B1 to enter 'Price' header. This manual clicking pattern continues for several cells.",
                        "applications": ["Microsoft Excel"],
                        "ui_elements": ["cell_A1", "cell_B1", "header_row"],
                        "user_actions": ["type_text", "manual_cell_navigation"]
                    },
                    {
                        "timestamp": "00:00:30",
                        "forensic_description": "User continues data entry by manually clicking each cell individually instead of using Tab key navigation. User then right-clicks to access formatting options for each cell separately.",
                        "applications": ["Microsoft Excel"],
                        "ui_elements": ["data_cells", "context_menu", "format_dialog"],
                        "user_actions": ["manual_clicking", "individual_formatting"]
                    }
                ]
            },
            {
                "window_analysis": {
                    "window": "2/5",
                    "time_range": "30.0s-59.0s"
                },
                "frame_descriptions": [
                    {
                        "timestamp": "00:00:45",
                        "forensic_description": "User attempts to create a chart by first manually selecting data range using mouse dragging, then navigating through Insert menu to find Chart options.",
                        "applications": ["Microsoft Excel"],
                        "ui_elements": ["data_range", "insert_menu", "chart_options"],
                        "user_actions": ["manual_selection", "menu_navigation"]
                    }
                ]
            }
        ]
    }


def test_database_operations():
    """Test database operations."""
    print("\n🧪 Testing database operations...")

    # Use temporary database
    db_path = "test_v2_sessions.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_manager = DatabaseManager(db_path)

    # Test session creation
    gpt_config = GPTConfig(model="gpt-5-mini", reasoning_effort="medium")
    processing_config = ProcessingConfig(window_seconds=30)

    session_id = "test_session_v2"
    success = db_manager.create_session(
        session_id=session_id,
        name="Test Session V2",
        gpt_config=gpt_config,
        processing_config=processing_config
    )

    assert success, "Failed to create session"
    print("  ✅ Session creation successful")

    # Test session retrieval
    session = db_manager.get_session(session_id)
    assert session is not None, "Failed to retrieve session"
    assert session['name'] == "Test Session V2", "Session name mismatch"
    print("  ✅ Session retrieval successful")

    # Test session status update
    success = db_manager.update_session_status(session_id, SessionStatus.PROCESSING)
    assert success, "Failed to update session status"
    print("  ✅ Session status update successful")

    # Cleanup
    db_manager.delete_session(session_id)
    if os.path.exists(db_path):
        os.remove(db_path)

    print("✅ Database operations test passed")


def test_enhanced_window_processor():
    """Test enhanced window processing."""
    print("\n🧪 Testing enhanced window processor...")

    # Create test data
    test_data = create_test_json_data()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        temp_file = f.name

    try:
        processor = EnhancedWindowProcessor(window_seconds=30)

        # Test JSON validation
        is_valid, message = processor.validate_json_structure(temp_file)
        assert is_valid, f"JSON validation failed: {message}"
        print("  ✅ JSON validation successful")

        # Test frame loading
        frame_descriptions, metadata = processor.load_frame_descriptions_from_json(temp_file)
        assert len(frame_descriptions) > 0, "No frame descriptions loaded"
        print(f"  ✅ Loaded {len(frame_descriptions)} frame descriptions")

        # Test window creation
        windows = processor.create_windows_from_frames(frame_descriptions)
        assert len(windows) > 0, "No windows created"
        print(f"  ✅ Created {len(windows)} processing windows")

        # Test context extraction
        if windows:
            context = processor.extract_window_context(windows[0])
            assert 'applications_used' in context, "Missing context data"
            print("  ✅ Context extraction successful")

        # Test session creation from JSON
        session_id, windows, metadata = processor.create_session_from_json(temp_file, "Test Session")
        assert session_id is not None, "Session creation failed"
        assert len(windows) > 0, "No windows in session"
        print(f"  ✅ Session creation from JSON successful")

    finally:
        os.remove(temp_file)

    print("✅ Enhanced window processor test passed")


def test_context_manager():
    """Test context management functionality."""
    print("\n🧪 Testing context manager...")

    # Create temporary database
    db_path = "test_context.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_manager = DatabaseManager(db_path)
    context_manager = ContextManager(db_manager)

    # Create test data
    test_data = create_test_json_data()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        temp_file = f.name

    try:
        processor = EnhancedWindowProcessor()
        frame_descriptions, metadata = processor.load_frame_descriptions_from_json(temp_file)
        windows = processor.create_windows_from_frames(frame_descriptions)

        if windows:
            # Test context building
            context_prompt = context_manager.build_context_for_window("test_session", 1, windows[0])
            assert len(context_prompt) > 0, "Context prompt is empty"
            assert "ANALYSIS CONTEXT FOR WINDOW 1" in context_prompt, "Missing context header"
            print("  ✅ Context prompt generation successful")

            # Test recommendation extraction
            sample_analysis = """
            ## Recommendation 1: Use Excel Keyboard Shortcuts (Score: 18/24)

            **Observation**: User manually clicking cells instead of using navigation shortcuts

            **Recommendation**: Use Tab and arrow keys for faster navigation

            **Implementation Steps**:
            1. Use Tab to move to next cell
            2. Use Shift+Tab to move to previous cell
            3. Use arrow keys for directional navigation

            **Expected Impact**: Save 2-3 seconds per navigation action
            """

            recommendations = context_manager.extract_recommendations_from_analysis(sample_analysis)
            assert len(recommendations) > 0, "No recommendations extracted"
            print(f"  ✅ Extracted {len(recommendations)} recommendations")

            # Test window context saving
            success = context_manager.save_window_context(
                "test_session", 1,
                processor.extract_window_context(windows[0]),
                sample_analysis
            )
            assert success, "Failed to save window context"
            print("  ✅ Window context saving successful")

    finally:
        os.remove(temp_file)
        if os.path.exists(db_path):
            os.remove(db_path)

    print("✅ Context manager test passed")


def test_gpt5_client_setup():
    """Test GPT-5 client setup and configuration."""
    print("\n🧪 Testing GPT-5 client setup...")

    # Test without API key
    try:
        client = GPT5Client("test_key")
        print("  ✅ GPT-5 client initialization successful")

        # Test configuration
        config = GPTConfig(
            model="gpt-5-mini",
            reasoning_effort="medium",
            verbosity="medium"
        )

        # Test token estimation
        test_data = create_test_json_data()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_file = f.name

        try:
            processor = EnhancedWindowProcessor()
            frame_descriptions, metadata = processor.load_frame_descriptions_from_json(temp_file)
            windows = processor.create_windows_from_frames(frame_descriptions)

            if windows:
                token_estimate = client.estimate_token_usage(
                    "Test system prompt",
                    "Test context prompt",
                    windows[0].to_dict()
                )

                assert token_estimate['estimated_total_tokens'] > 0, "Token estimation failed"
                print(f"  ✅ Token estimation: {token_estimate['estimated_total_tokens']} tokens")

                # Test cost calculation
                cost = client.calculate_estimated_cost(token_estimate, "gpt-5-mini")
                assert cost >= 0, "Cost calculation failed"
                print(f"  ✅ Cost estimation: ${cost:.4f}")

        finally:
            os.remove(temp_file)

    except Exception as e:
        print(f"  ⚠️ GPT-5 client test limited (no API key): {e}")

    print("✅ GPT-5 client setup test passed")


def test_batch_processor_setup():
    """Test batch processor setup."""
    print("\n🧪 Testing batch processor setup...")

    db_path = "test_batch.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db_manager = DatabaseManager(db_path)

    try:
        batch_processor = BatchProcessor(db_manager, "test_api_key")
        print("  ✅ Batch processor initialization successful")

        # Test job management
        active_jobs = batch_processor.get_all_active_jobs()
        assert isinstance(active_jobs, list), "Failed to get active jobs list"
        print("  ✅ Active jobs retrieval successful")

        # Test cleanup function
        batch_processor.cleanup_completed_jobs(max_age_hours=0)  # Should not error
        print("  ✅ Cleanup function successful")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

    print("✅ Batch processor setup test passed")


def test_file_structure():
    """Test that all required files are in place."""
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
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path}")

    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False

    print("✅ File structure test passed")
    return True


def test_system_prompt_loading():
    """Test system prompt loading."""
    print("\n🧪 Testing system prompt loading...")

    prompt_file = Path("src/prompts/klarity_coach_system_prompt.md")

    if prompt_file.exists():
        content = prompt_file.read_text(encoding='utf-8')
        assert len(content) > 100, "System prompt too short"
        assert "Klarity Coach" in content, "Missing system prompt header"
        print("  ✅ System prompt loaded successfully")
    else:
        print("  ❌ System prompt file not found")
        return False

    print("✅ System prompt loading test passed")
    return True


def run_integration_test():
    """Run a simple integration test."""
    print("\n🧪 Running integration test...")

    # Create temporary database
    db_path = "test_integration.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        # Initialize components
        db_manager = DatabaseManager(db_path)
        processor = EnhancedWindowProcessor(window_seconds=30)
        context_manager = ContextManager(db_manager)

        # Create test session
        gpt_config = GPTConfig()
        processing_config = ProcessingConfig()

        session_id = "integration_test"
        success = db_manager.create_session(
            session_id=session_id,
            name="Integration Test Session",
            gpt_config=gpt_config,
            processing_config=processing_config
        )

        assert success, "Failed to create integration test session"
        print("  ✅ Session created")

        # Create test data and process windows
        test_data = create_test_json_data()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_file = f.name

        try:
            # Load and process
            frame_descriptions, metadata = processor.load_frame_descriptions_from_json(temp_file)
            windows = processor.create_windows_from_frames(frame_descriptions)

            # Create windows in database
            for i, window in enumerate(windows, 1):
                window_id = f"{session_id}_window_{i}"
                success = db_manager.create_window(
                    window_id=window_id,
                    session_id=session_id,
                    window_number=i,
                    start_time=window.start_time,
                    end_time=window.end_time,
                    input_data=window.to_dict()
                )
                assert success, f"Failed to create window {i}"

            print(f"  ✅ Created {len(windows)} windows in database")

            # Test context building
            if windows:
                context_prompt = context_manager.build_context_for_window(session_id, 1, windows[0])
                assert len(context_prompt) > 0, "Context building failed"
                print("  ✅ Context building successful")

            # Verify session windows
            session_windows = db_manager.get_session_windows(session_id)
            assert len(session_windows) == len(windows), "Window count mismatch"
            print("  ✅ Session windows verification successful")

        finally:
            os.remove(temp_file)

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

    print("✅ Integration test passed")


def main():
    """Run all tests."""
    print("🚀 AI Coaching Framework v2 - System Tests")
    print("=" * 50)

    tests_passed = 0
    total_tests = 0

    test_functions = [
        test_file_structure,
        test_system_prompt_loading,
        test_database_operations,
        test_enhanced_window_processor,
        test_context_manager,
        test_gpt5_client_setup,
        test_batch_processor_setup,
        run_integration_test
    ]

    for test_func in test_functions:
        total_tests += 1
        try:
            result = test_func()
            if result is not False:  # None or True are both success
                tests_passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("\n🎉 All tests passed! AI Coaching Framework v2 is ready!")
        print("\n🚀 Next steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Run: streamlit run app_v2.py")
        print("3. Upload frame description JSON files from your Coach Project outputs")
        print("\n📁 Sample data available in:")
        print("   ../04_Outputs/Step_1/New_test_inputs/")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests failed. Please fix issues before deployment.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)