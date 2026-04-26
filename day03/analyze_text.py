#!/usr/bin/env python3
"""
Text analyzer that uses distribution_of_letters module.
Accepts text as a command line parameter and displays letter distribution.

Usage: python analyze_text.py "Your text here"
"""

import sys
from distribution_of_letters import letter_distribution, print_distribution

def main():
    # Check if command line argument is provided
    if len(sys.argv) < 2:
        print("Usage: python analyze_text.py \"Your text here\"")
        print("Example: python analyze_text.py \"Hello World!\"")
        sys.exit(1)
    
    # Join all command line arguments (in case text has spaces)
    text = " ".join(sys.argv[1:])
    
    # Use the imported functions to analyze the text
    distribution, total = letter_distribution(text)
    
    print(f"Analyzing text: {text}\n")
    print_distribution(distribution, total)

if __name__ == "__main__":
    main()