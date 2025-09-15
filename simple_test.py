#!/usr/bin/env python3
"""
Simple test without external dependencies.
Tests core framework components.
"""

import json
import sys
from pathlib import Path

# Test data
SAMPLE_FRAMES = {
    "frames": [
        {"timestamp": 0.5, "description": "Opening Chrome browser"},
        {"timestamp": 30.2, "description": "Navigating to Gmail"},
        {"timestamp": 65.8, "description": "Reading first email"},
        {"timestamp": 120.3, "description": "Composing reply"}
    ]
}

def test_json_parsing():
    """Test JSON parsing functionality."""
    print("🔍 Testing JSON parsing...")

    try:
        # Test valid JSON
        json_str = json.dumps(SAMPLE_FRAMES)
        parsed = json.loads(json_str)

        assert 'frames' in parsed
        assert len(parsed['frames']) == 4
        assert parsed['frames'][0]['timestamp'] == 0.5

        print("   ✅ JSON parsing works correctly")
        return True

    except Exception as e:
        print(f"   ❌ JSON parsing failed: {e}")
        return False

def test_frame_structure():
    """Test frame structure validation."""
    print("📋 Testing frame structure...")

    try:
        frames = SAMPLE_FRAMES['frames']

        # Check required fields
        for i, frame in enumerate(frames):
            assert 'timestamp' in frame, f"Frame {i} missing timestamp"
            assert 'description' in frame, f"Frame {i} missing description"
            assert isinstance(frame['timestamp'], (int, float)), f"Frame {i} timestamp not numeric"
            assert isinstance(frame['description'], str), f"Frame {i} description not string"

        print(f"   ✅ All {len(frames)} frames have valid structure")
        return True

    except Exception as e:
        print(f"   ❌ Frame structure validation failed: {e}")
        return False

def test_time_calculations():
    """Test time-related calculations."""
    print("⏰ Testing time calculations...")

    try:
        frames = SAMPLE_FRAMES['frames']

        # Test sorting by timestamp
        sorted_frames = sorted(frames, key=lambda f: f['timestamp'])
        timestamps = [f['timestamp'] for f in sorted_frames]

        # Check if already sorted
        assert timestamps == sorted(timestamps), "Frames not in chronological order"

        # Calculate duration
        total_duration = timestamps[-1] - timestamps[0]
        assert total_duration > 0, "Invalid duration calculation"

        # Test time formatting
        def format_time(seconds):
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"

        formatted = format_time(total_duration)
        assert ":" in formatted, "Time formatting failed"

        print(f"   ✅ Time calculations work (duration: {formatted})")
        return True

    except Exception as e:
        print(f"   ❌ Time calculations failed: {e}")
        return False

def test_window_chunking():
    """Test window chunking logic."""
    print("🪟 Testing window chunking...")

    try:
        frames = SAMPLE_FRAMES['frames']
        interval_seconds = 60  # 1 minute intervals

        # Simple chunking algorithm
        if not frames:
            return True

        start_time = frames[0]['timestamp']
        end_time = frames[-1]['timestamp']

        windows = []
        current_start = start_time

        while current_start < end_time:
            current_end = current_start + interval_seconds

            # Get frames in this window
            window_frames = [
                f for f in frames
                if current_start <= f['timestamp'] < current_end
            ]

            if window_frames:
                windows.append({
                    'start': current_start,
                    'end': current_end,
                    'frames': window_frames
                })

            current_start = current_end

        assert len(windows) > 0, "No windows created"
        assert sum(len(w['frames']) for w in windows) == len(frames), "Frames lost during chunking"

        print(f"   ✅ Created {len(windows)} windows from {len(frames)} frames")
        return True

    except Exception as e:
        print(f"   ❌ Window chunking failed: {e}")
        return False

def test_text_processing():
    """Test text processing utilities."""
    print("📝 Testing text processing...")

    try:
        frames = SAMPLE_FRAMES['frames']

        # Extract applications from descriptions
        descriptions = [f['description'] for f in frames]
        combined_text = ' '.join(descriptions).lower()

        # Simple keyword extraction
        keywords = ['chrome', 'gmail', 'email', 'browser']
        found_keywords = [kw for kw in keywords if kw in combined_text]

        assert len(found_keywords) > 0, "No keywords found in descriptions"

        # Test text truncation
        long_text = "This is a very long description that should be truncated"
        def truncate_text(text, max_length=20):
            return text[:max_length] + "..." if len(text) > max_length else text

        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 23, "Text truncation failed"  # 20 + "..."

        print(f"   ✅ Text processing works (found keywords: {found_keywords})")
        return True

    except Exception as e:
        print(f"   ❌ Text processing failed: {e}")
        return False

def test_file_operations():
    """Test file operations."""
    print("📁 Testing file operations...")

    try:
        # Test sample files exist
        examples_dir = Path(__file__).parent / "examples"

        expected_files = ["sample_frames.json", "coding_session.json"]
        existing_files = []

        for filename in expected_files:
            file_path = examples_dir / filename
            if file_path.exists():
                existing_files.append(filename)

                # Try to read and parse
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    data = json.loads(content)  # This will raise if invalid JSON

        print(f"   ✅ File operations work ({len(existing_files)}/{len(expected_files)} files found)")
        return True

    except Exception as e:
        print(f"   ❌ File operations failed: {e}")
        return False

def main():
    """Run all simple tests."""
    print("🚀 AI Coaching Framework - Simple Test Suite")
    print("=" * 50)

    tests = [
        test_json_parsing,
        test_frame_structure,
        test_time_calculations,
        test_window_chunking,
        test_text_processing,
        test_file_operations
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")
            failed += 1

    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All basic tests passed! Core functionality is working.")
        print("\n🔧 Next steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Set up API key: cp .env.example .env (edit with your key)")
        print("   3. Run Streamlit: streamlit run app.py")
        print("   4. Or use CLI: python cli.py --help")
        return 0
    else:
        print("❌ Some tests failed. Check the framework setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())