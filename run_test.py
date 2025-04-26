import sys
from io import StringIO
from solar_calculator import main

def run_test():
    # Save the original stdin
    original_stdin = sys.stdin
    
    # Create a StringIO object with our test inputs
    test_inputs = StringIO("6.6\n4936\n0\n31\n6\n3\n")  # 1 for common mounting configuration
    
    # Redirect stdin to our test inputs
    sys.stdin = test_inputs
    
    try:
        # Run the main function with our test inputs
        main()
    finally:
        # Restore the original stdin
        sys.stdin = original_stdin

if __name__ == "__main__":
    print("Running solar calculator test with parameters:")
    print("System size: 6.6 kW")
    print("System cost: $4,936")
    print("System age: 0 years (new system)")
    print("Tilt angle: 31°")
    print("Azimuth angle: 6°")
    print("Mounting configuration: Common")
    print("\nStarting simulation...\n")
    
    run_test() 