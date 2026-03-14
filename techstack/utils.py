"""
utils.py — Shared utilities for the Tech Stack Analyzer.
"""

from __future__ import annotations

import os
import re


def find_system_font(bold: bool = False) -> str | None:
    """
    Return the path to a TrueType font available on the current system,
    or ``None`` if no suitable font is found (callers should fall back to
    the library's built-in default).

    Searches common font locations on Linux, macOS, and Windows.
    Prefers Lato (modern, clean) then falls back to DejaVu / Liberation.
    """
    candidates_bold = [
        # Lato — clean modern sans-serif, preferred
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
        # DejaVu fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    candidates_regular = [
        # Lato — clean modern sans-serif, preferred
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Light.ttf",
        # DejaVu fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in (candidates_bold if bold else candidates_regular):
        if os.path.exists(path):
            return path
    return None


def slugify(text: str) -> str:
    """Convert a string to a safe, lowercase filename component."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
