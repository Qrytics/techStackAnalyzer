#!/usr/bin/env python3
"""
analyze.py — backward-compatible shim; delegates to techstack.cli.

Preferred usage (after `pip install .`):
    techstack <github-repo-url> [options]

Legacy usage:
    python analyze.py <github-repo-url> [options]
"""

from techstack.cli import main

if __name__ == "__main__":
    main()
