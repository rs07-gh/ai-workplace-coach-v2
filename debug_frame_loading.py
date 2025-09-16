#!/usr/bin/env python3

import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from enhanced_window_processor import EnhancedWindowProcessor

def debug_frame_loading():
    processor = EnhancedWindowProcessor()
    json_file = '/Users/rs07/Desktop/Projects/Coach Project/04_Outputs/Step_1/New_test_inputs/Stanley - Manual Prompting_hybrid (1).json'

    print("Loading JSON file...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Windows count: {len(data.get('windows', []))}")

    # Test the exact code path from the processor
    frame_descriptions = []
    windows_data = data.get('windows', [])

    print(f"Processing {len(windows_data)} windows...")

    for i, window_data in enumerate(windows_data[:2]):  # Just test first 2 windows
        print(f"\nWindow {i+1}:")
        print(f"  Window data type: {type(window_data)}")
        print(f"  Window keys: {list(window_data.keys())}")

        window_frames = window_data.get('frame_descriptions', [])
        print(f"  Frame descriptions count: {len(window_frames)}")

        for j, frame_data in enumerate(window_frames):
            print(f"    Frame {j+1} type: {type(frame_data)}")
            print(f"    Frame {j+1} is dict: {isinstance(frame_data, dict)}")

            if isinstance(frame_data, dict):
                print(f"    Frame {j+1} keys: {list(frame_data.keys())}")
                timestamp = frame_data.get('timestamp', '00:00:00')
                print(f"    Frame {j+1} timestamp: {timestamp}")

                # Test timestamp parsing
                timestamp_seconds = processor.parse_timestamp_to_seconds(timestamp)
                print(f"    Frame {j+1} timestamp_seconds: {timestamp_seconds}")
            else:
                print(f"    ERROR: Frame {j+1} is not a dict: {frame_data}")
                return False

    print("\nAll frames processed successfully in debug mode!")
    return True

if __name__ == "__main__":
    debug_frame_loading()