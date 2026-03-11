"""
video_generator.py — Assemble the final explainer video with moviepy.

One slide per narration section:
  - Section title (text overlay)
  - Relevant tech logos arranged in a grid
  - Section narration audio as voice-over
  - Fade-in / fade-out transition between slides

Exports a single .mp4 file.

Compatible with moviepy >= 2.x.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from moviepy import (  # type: ignore[import]
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
    vfx,
)
from PIL import Image  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VIDEO_W = 1280
VIDEO_H = 720
FPS = 24
FADE_DURATION = 0.5  # seconds

BG_COLOR = (15, 15, 35)           # dark navy
TITLE_COLOR = "white"
TITLE_FONT_SIZE = 56
SUBTITLE_FONT_SIZE = 20
MIN_SLIDE_DURATION = 3.0           # seconds (used when audio is missing)
LOGO_MAX_SIZE = 160                # px, logo thumbnail max dimension
LOGO_PADDING = 20                  # px between logos
LOGO_TOP_MARGIN = 220              # px from top of frame


def _find_font(bold: bool = False) -> str | None:
    """Return a font path available on the system, or None to let moviepy pick."""
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    candidates_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in (candidates_bold if bold else candidates_regular):
        if os.path.exists(p):
            return p
    return None


def _resize_image_to_box(src: str, max_size: int) -> Image.Image:
    """Return a PIL Image resized to fit within a square of *max_size*."""
    img = Image.open(src).convert("RGBA")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    return img


def _arrange_logos(
    logo_paths: list[str],
    frame_w: int,
    frame_h: int,
    top_margin: int,
) -> list[dict[str, Any]]:
    """
    Calculate (x, y) positions to place logo thumbnails in a centred grid.

    Returns a list of dicts: [{"path": str, "x": int, "y": int, "size": (w, h)}]
    """
    if not logo_paths:
        return []

    max_logos = 8
    paths = logo_paths[:max_logos]
    items = []
    for p in paths:
        try:
            img = _resize_image_to_box(p, LOGO_MAX_SIZE)
            items.append({"path": p, "img": img, "w": img.width, "h": img.height})
        except Exception:
            pass

    if not items:
        return []

    cols = min(len(items), 4)
    rows = (len(items) + cols - 1) // cols

    total_w = cols * LOGO_MAX_SIZE + (cols - 1) * LOGO_PADDING
    start_x = (frame_w - total_w) // 2

    available_h = frame_h - top_margin - 20
    row_h = LOGO_MAX_SIZE + LOGO_PADDING

    result = []
    for idx, item in enumerate(items):
        col = idx % cols
        row = idx // cols
        x = start_x + col * (LOGO_MAX_SIZE + LOGO_PADDING)
        y = top_margin + row * row_h + (available_h - rows * row_h) // 2
        result.append({
            "path": item["path"],
            "x": x,
            "y": y,
            "size": (item["w"], item["h"]),
        })
    return result


def _make_slide(
    section: dict[str, Any],
    logo_map: dict[str, str],
    duration: float,
) -> CompositeVideoClip:
    """Build a single slide as a CompositeVideoClip (moviepy 2.x API)."""
    title = section["title"]
    techs = section.get("techs", [])

    # Background
    bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=BG_COLOR, duration=duration)

    clips: list[Any] = [bg]

    # Title text
    title_font = _find_font(bold=True)
    try:
        title_kwargs: dict[str, Any] = {
            "text": title,
            "font_size": TITLE_FONT_SIZE,
            "color": TITLE_COLOR,
            "method": "caption",
            "size": (VIDEO_W - 120, None),
            "duration": duration,
        }
        if title_font:
            title_kwargs["font"] = title_font
        title_clip = TextClip(**title_kwargs).with_position(("center", 60))
        clips.append(title_clip)
    except Exception as e:
        print(f"    [VIDEO] TextClip failed for title {title!r}: {e}")

    # Narration text (subtitle strip at bottom)
    narration = section.get("text", "")
    if narration:
        wrapped = "\n".join(textwrap.wrap(narration, width=90))
        regular_font = _find_font(bold=False)
        try:
            narr_kwargs: dict[str, Any] = {
                "text": wrapped,
                "font_size": SUBTITLE_FONT_SIZE,
                "color": "#CCCCCC",
                "method": "caption",
                "size": (VIDEO_W - 80, None),
                "duration": duration,
            }
            if regular_font:
                narr_kwargs["font"] = regular_font
            narr_clip = TextClip(**narr_kwargs).with_position(("center", VIDEO_H - 140))
            clips.append(narr_clip)
        except Exception as e:
            print(f"    [VIDEO] Narration TextClip failed: {e}")

    # Logo images
    logo_paths = [logo_map[t] for t in techs if t in logo_map]
    logo_positions = _arrange_logos(logo_paths, VIDEO_W, VIDEO_H - 140, LOGO_TOP_MARGIN)

    for lp in logo_positions:
        try:
            img_clip = (
                ImageClip(lp["path"], duration=duration)
                .with_effects([vfx.Resize(lp["size"])])
                .with_position((lp["x"], lp["y"]))
            )
            clips.append(img_clip)
        except Exception as e:
            print(f"    [VIDEO] Logo clip failed ({lp['path']}): {e}")

    composite = CompositeVideoClip(clips, size=(VIDEO_W, VIDEO_H))

    # Fade in / out
    composite = composite.with_effects([
        vfx.FadeIn(FADE_DURATION),
        vfx.FadeOut(FADE_DURATION),
    ])

    # Attach audio
    audio_path = section.get("audio_path", "")
    if audio_path and os.path.exists(audio_path):
        try:
            audio = AudioFileClip(audio_path).subclipped(0, duration)
            composite = composite.with_audio(audio)
        except Exception as e:
            print(f"    [VIDEO] Audio attachment failed: {e}")

    return composite


def generate_video(
    sections: list[dict[str, Any]],
    logo_map: dict[str, str],
    output_path: str | Path,
) -> str:
    """
    Assemble and export the final explainer video.

    Parameters
    ----------
    sections    : sections list (each augmented with audio_path, audio_duration)
    logo_map    : {tech_label: local_image_path}
    output_path : destination .mp4 file path

    Returns
    -------
    Absolute path to the exported .mp4
    """
    slides = []
    for section in sections:
        duration = max(
            MIN_SLIDE_DURATION,
            section.get("audio_duration", MIN_SLIDE_DURATION),
        )
        print(f"  [VIDEO] Building slide: {section['title']!r} ({duration:.1f}s)")
        slide = _make_slide(section, logo_map, duration)
        slides.append(slide)

    if not slides:
        raise RuntimeError("No slides were generated — cannot produce video.")

    final = concatenate_videoclips(slides, method="compose")

    out_path = str(output_path)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"  [VIDEO] Exporting → {out_path} …")
    final.write_videofile(
        out_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(Path(out_path).parent / "_temp_audio.m4a"),
        remove_temp=True,
        logger=None,  # suppress moviepy progress bars
    )
    print(f"  [VIDEO] Done → {out_path}")
    return out_path
