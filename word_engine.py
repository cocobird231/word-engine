#!/usr/bin/env python3
"""
Word Engine - Top-level entry point.
Run from the word-engine/ directory:
    python word_engine.py qc --md refine.md --params params.yaml
"""
import sys
import os

# Ensure the project root is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.cli import main

if __name__ == "__main__":
    main()
