#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from main import analyze_bias

# Test the new format
test_text = "This politician is terrible and should be fired immediately."
print(f"Testing with text: {test_text}")

try:
    result = analyze_bias(test_text)
    print(f"Result: {result}")
    print(f"Type: {type(result)}")

    if isinstance(result, list):
        if len(result) > 0:
            print("First result keys:", list(result[0].keys()) if result[0] else "Empty result")
            if result[0] and 'text' in result[0]:
                print("✓ New format working - found 'text' field")
                print(f"Problematic text: '{result[0]['text']}'")
            else:
                print("✗ Old format still present - missing 'text' field")
        else:
            print("No bias detected (empty list)")
    else:
        print("Result is not a list")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()