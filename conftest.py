"""
Pytest configuration for VAJRA backend.
Adds the project root to sys.path so that 'import backend.xxx' works
without installing the package.
"""
import sys
import os

# Insert the project root (one level above the backend/ directory)
# so that `from backend.xxx import ...` resolves correctly.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
