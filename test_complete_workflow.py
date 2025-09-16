#!/usr/bin/env python3
"""
Complete workflow test for AI Coaching Framework v2
Tests the full pipeline from JSON loading to session processing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import DatabaseManager, GPTConfig, ProcessingConfig, SessionStatus
from enhanced_window_processor import EnhancedWindowProcessor
from context_manager import ContextManager
from gpt5_client import GPT5Client

def test_complete_workflow():
    """Test the complete workflow with real data."""
    print("🧪 Testing complete workflow with real data...")

    # Use smaller test file for workflow testing
    test_file = '/Users/rs07/Desktop/Projects/Coach Project/04_Outputs/Step_1/New_test_inputs/Stanley - Manual Prompting_hybrid (1).json'
    db_path = "test_workflow.db"

    if os.path.exists(db_path):
        os.remove(db_path)

    try:
        # Initialize components
        print("  1. Initializing components...")
        db_manager = DatabaseManager(db_path)
        processor = EnhancedWindowProcessor(window_seconds=30)
        context_manager = ContextManager(db_manager)
        gpt5_client = GPT5Client("test_api_key_for_testing")

        # Test JSON processing
        print("  2. Processing JSON file...")
        frames, metadata = processor.load_frame_descriptions_from_json(test_file)
        print(f"     ✅ Loaded {len(frames)} frame descriptions")
        print(f"     ✅ Video duration: {metadata.get('duration_seconds', 0):.1f} seconds")

        # Create processing windows
        print("  3. Creating processing windows...")
        windows = processor.create_windows_from_frames(frames)
        print(f"     ✅ Created {len(windows)} windows")

        # Create session
        print("  4. Creating database session...")
        gpt_config = GPTConfig(model="gpt-5-mini")
        processing_config = ProcessingConfig(window_seconds=30)

        session_id = f"test_workflow_{metadata.get('video', 'unknown').replace('.mp4', '')}"
        success = db_manager.create_session(
            session_id=session_id,
            name=f"Workflow Test - {metadata.get('video', 'Unknown')}",
            gpt_config=gpt_config,
            processing_config=processing_config,
            input_file_path=test_file
        )

        if not success:
            print("     ❌ Failed to create session")
            return False

        print(f"     ✅ Created session: {session_id}")

        # Process windows and save to database
        print("  5. Processing windows and saving to database...")
        for i, window in enumerate(windows[:3], 1):  # Test first 3 windows only
            window_id = f"{session_id}_window_{i}"

            # Create window in database
            success = db_manager.create_window(
                window_id=window_id,
                session_id=session_id,
                window_number=i,
                start_time=window.start_time,
                end_time=window.end_time,
                input_data=window.to_dict()
            )

            if success:
                print(f"     ✅ Created window {i}: {window.start_time:.1f}s - {window.end_time:.1f}s")
            else:
                print(f"     ❌ Failed to create window {i}")

        # Test context building
        print("  6. Testing context management...")
        if windows:
            context_prompt = context_manager.build_context_for_window(session_id, 1, windows[0])
            print(f"     ✅ Built context prompt ({len(context_prompt)} characters)")

            # Test context extraction
            window_context = processor.extract_window_context(windows[0])
            print(f"     ✅ Extracted context: {len(window_context.get('applications', []))} applications")

            # Test recommendation extraction (simulate analysis)
            sample_analysis = f"""
            ## Recommendation 1: Use Keyboard Shortcuts (Score: 18/24)

            **Observation**: User manually navigating with mouse clicks instead of using keyboard shortcuts

            **Recommendation**: Learn and use Tab and Enter key combinations for faster navigation

            **Implementation Steps**:
            1. Use Tab to move between fields
            2. Use Enter to confirm selections
            3. Use Ctrl+A to select all text

            **Expected Impact**: Save 2-3 seconds per navigation action
            """

            success = context_manager.save_window_context(
                session_id=session_id,
                window_number=1,
                window_context=window_context,
                analysis_result=sample_analysis
            )

            if success:
                print("     ✅ Saved context and recommendations")
            else:
                print("     ❌ Failed to save context")

        # Test token estimation
        print("  7. Testing GPT-5 integration...")
        if windows:
            token_estimate = gpt5_client.estimate_token_usage(
                "System prompt for testing",
                "Context prompt for testing",
                windows[0].to_dict()
            )

            estimated_cost = gpt5_client.calculate_estimated_cost(token_estimate, "gpt-5-mini")
            print(f"     ✅ Token estimate: {token_estimate['estimated_total_tokens']} tokens")
            print(f"     ✅ Estimated cost: ${estimated_cost:.4f}")

        # Test session retrieval
        print("  8. Testing session retrieval...")
        session = db_manager.get_session(session_id)
        if session:
            print(f"     ✅ Retrieved session: {session['name']}")

        session_windows = db_manager.get_session_windows(session_id)
        print(f"     ✅ Session has {len(session_windows)} windows")

        # Test workflow summary
        print("  9. Testing workflow summary...")
        summary = context_manager.get_session_workflow_summary(session_id)
        print(f"     ✅ Workflow summary: {summary['total_recommendations']} recommendations")
        print(f"     ✅ Tools identified: {len(summary['tools_identified'])}")

        print("\n🎉 Complete workflow test PASSED!")
        print(f"\n📊 Summary:")
        print(f"   • Processed {len(frames)} frames")
        print(f"   • Created {len(windows)} windows")
        print(f"   • Session ID: {session_id}")
        print(f"   • Database: {db_path}")

        return True

    except Exception as e:
        print(f"\n❌ Workflow test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)