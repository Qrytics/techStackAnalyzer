"""
video_generator.py — Assemble the final explainer video with moviepy.

Each slide is rendered entirely with PIL (no ImageMagick/TextClip spawning):
  - Dark gradient background with a coloured accent stripe
  - Section title + subtitle text
  - Relevant tech logos arranged in a centred grid
  - Section narration audio as voice-over
  - Fade-in / fade-out transition between slides

Exports a single .mp4 file using the ultrafast libx264 preset for speed.

Compatible with moviepy >= 2.x.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]
from moviepy import (  # type: ignore[import]
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)

from techstack.utils import find_system_font

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VIDEO_W = 1280
VIDEO_H = 720
FPS = 15                  # 15 fps is plenty for a slideshow and encodes ~2× faster
FADE_DURATION = 0.5       # seconds

# Colour palette (RGB)
BG_TOP    = (10, 12, 35)   # deep navy
BG_BOTTOM = (20, 24, 60)   # slightly lighter navy
ACCENT_COLORS = [
    (64, 190, 255),    # electric blue
    (120, 86, 255),    # violet
    (0, 220, 180),     # teal
    (255, 120, 60),    # orange
    (255, 80, 140),    # pink
    (80, 200, 120),    # green
    (255, 200, 50),    # yellow
    (180, 90, 255),    # purple
]

TITLE_FONT_SIZE  = 62
BODY_FONT_SIZE   = 19
LABEL_FONT_SIZE  = 13

MIN_SLIDE_DURATION = 3.0    # seconds (used when audio is missing)
LOGO_MAX_SIZE      = 130    # px, logo thumbnail max dimension
LOGO_PADDING       = 24     # px gap between logos
LOGO_TOP_MARGIN    = 230    # px from top of frame to first logo row


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = find_system_font(bold=bold)
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Frame rendering (pure PIL — all drawing on RGBA canvas)
# ---------------------------------------------------------------------------
def _gradient_bg(w: int, h: int) -> Image.Image:
    """Render a top-to-bottom gradient background (RGBA)."""
    top = np.array(BG_TOP, dtype=np.float32)
    bot = np.array(BG_BOTTOM, dtype=np.float32)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / (h - 1)
        arr[y, :] = ((1 - t) * top + t * bot).astype(np.uint8)
    rgb = Image.fromarray(arr, "RGB")
    return rgb.convert("RGBA")


def _draw_accent_bar(draw: ImageDraw.ImageDraw, color: tuple[int, int, int], w: int) -> None:
    """Draw a thin coloured bar at the top of the frame (fully opaque)."""
    draw.rectangle([0, 0, w, 5], fill=(*color, 255))


def _draw_title(
    draw: ImageDraw.ImageDraw,
    frame: Image.Image,
    title: str,
    accent: tuple[int, int, int],
    w: int,
    font_bold: Any,
    font_counter: Any,
    section_num: int,
    total_sections: int,
) -> None:
    """Render the slide title and a section progress pill (RGBA canvas)."""
    # Section counter pill (top-right corner)
    pill_text = f"{section_num} / {total_sections}"
    pb = draw.textbbox((0, 0), pill_text, font=font_counter)
    pill_w = pb[2] - pb[0] + 20
    pill_h = pb[3] - pb[1] + 8
    pill_x = w - pill_w - 28
    pill_y = 18
    # Semi-transparent pill via alpha_composite on the RGBA frame
    pill_overlay = Image.new("RGBA", (pill_w, pill_h), (*accent, 190))
    frame.alpha_composite(pill_overlay, (pill_x, pill_y))
    draw.text((pill_x + 10, pill_y + 4), pill_text, fill=(255, 255, 255, 255), font=font_counter)

    # Title text
    title_y = 38
    draw.text((60, title_y), title, fill=(255, 255, 255, 255), font=font_bold)

    # Accent underline
    tb = draw.textbbox((60, title_y), title, font=font_bold)
    line_y = tb[3] + 10
    line_end = min(tb[2] + 20, w - 60)
    draw.line([(60, line_y), (line_end, line_y)], fill=(*accent, 255), width=3)
    # Faded dotted extension
    for i in range(4):
        x = line_end + i * 8
        alpha = max(0, 180 - i * 45)
        draw.line([(x, line_y), (x + 6, line_y)], fill=(*accent, alpha), width=3)


def _draw_narration_panel(
    frame: Image.Image,
    text: str,
    w: int,
    h: int,
    font: Any,
) -> None:
    """Composite a frosted dark panel at the bottom of the RGBA *frame*."""
    panel_h = 130
    panel_y = h - panel_h

    # Semi-transparent dark overlay via alpha_composite
    panel = Image.new("RGBA", (w, panel_h), (5, 8, 25, 215))
    frame.alpha_composite(panel, (0, panel_y))

    draw = ImageDraw.Draw(frame)
    # Thin separator line
    draw.line([(0, panel_y), (w, panel_y)], fill=(80, 80, 120, 255), width=1)

    wrapped = "\n".join(textwrap.wrap(text, width=100))
    draw.text((40, panel_y + 14), wrapped, fill=(210, 215, 235, 255), font=font)


def _paste_logos(
    frame: Image.Image,
    logo_paths: list[str],
    frame_w: int,
    frame_h: int,
    top_margin: int,
    bottom_limit: int,
) -> None:
    """Composite tech logos onto *frame* (RGBA) in a centred, evenly-spaced grid."""
    if not logo_paths:
        return

    max_logos = 8
    paths = logo_paths[:max_logos]
    imgs: list[Image.Image] = []
    for p in paths:
        try:
            img = Image.open(p).convert("RGBA")
            img.thumbnail((LOGO_MAX_SIZE, LOGO_MAX_SIZE), Image.LANCZOS)
            imgs.append(img)
        except (OSError, IOError, Exception):
            pass

    if not imgs:
        return

    cols = min(len(imgs), 4)
    rows = (len(imgs) + cols - 1) // cols

    total_w = cols * LOGO_MAX_SIZE + (cols - 1) * LOGO_PADDING
    start_x = (frame_w - total_w) // 2
    available_h = bottom_limit - top_margin
    row_h = LOGO_MAX_SIZE + LOGO_PADDING
    start_y = top_margin + max(0, (available_h - rows * row_h) // 2)

    draw = ImageDraw.Draw(frame)

    for idx, img in enumerate(imgs):
        col = idx % cols
        row = idx // cols
        cx = start_x + col * (LOGO_MAX_SIZE + LOGO_PADDING) + (LOGO_MAX_SIZE - img.width) // 2
        cy = start_y + row * row_h + (LOGO_MAX_SIZE - img.height) // 2

        # Drop shadow (semi-transparent black)
        shadow = Image.new("RGBA", img.size, (0, 0, 0, 100))
        frame.alpha_composite(shadow, (cx + 3, cy + 3))

        # Logo image
        frame.alpha_composite(img, (cx, cy))

        # Subtle card outline (RGB-only since it's a solid line)
        draw.rounded_rectangle(
            [cx - 6, cy - 6, cx + img.width + 6, cy + img.height + 6],
            radius=10, outline=(60, 65, 100), width=1,
        )


def _render_slide_frame(
    section: dict[str, Any],
    logo_map: dict[str, str],
    section_index: int,
    total_sections: int,
) -> np.ndarray:
    """
    Render one slide as a numpy RGB array using PIL.

    All drawing is performed on an RGBA canvas; the result is converted to
    RGB at the end before being handed off to moviepy.
    """
    accent = ACCENT_COLORS[section_index % len(ACCENT_COLORS)]
    title  = section["title"]
    text   = section.get("text", "")
    techs  = section.get("techs", [])

    # Fonts
    font_bold    = _load_font(TITLE_FONT_SIZE,  bold=True)
    font_regular = _load_font(BODY_FONT_SIZE,   bold=False)
    font_label   = _load_font(LABEL_FONT_SIZE,  bold=False)
    font_counter = _load_font(14,               bold=False)

    # RGBA canvas — gradient background
    frame = _gradient_bg(VIDEO_W, VIDEO_H)   # RGBA
    draw  = ImageDraw.Draw(frame)

    # Subtle grid pattern overlay (RGBA fill works on RGBA canvas)
    for x in range(0, VIDEO_W, 40):
        draw.line([(x, 0), (x, VIDEO_H)], fill=(255, 255, 255, 6), width=1)
    for y in range(0, VIDEO_H, 40):
        draw.line([(0, y), (VIDEO_W, y)], fill=(255, 255, 255, 6), width=1)

    _draw_accent_bar(draw, accent, VIDEO_W)
    _draw_title(draw, frame, title, accent, VIDEO_W, font_bold, font_counter, section_index + 1, total_sections)

    # Branding watermark (bottom-right, faint)
    brand = "Tech Stack Analyzer"
    bb = draw.textbbox((0, 0), brand, font=font_label)
    bw = bb[2] - bb[0]
    draw.text((VIDEO_W - bw - 20, VIDEO_H - 22), brand, fill=(80, 90, 130, 200), font=font_label)

    # Logos (composited onto RGBA frame)
    logo_paths = [logo_map[t] for t in techs if t in logo_map]
    _paste_logos(frame, logo_paths, VIDEO_W, VIDEO_H,
                 top_margin=LOGO_TOP_MARGIN, bottom_limit=VIDEO_H - 145)

    # Narration text panel (composited onto RGBA frame)
    if text:
        _draw_narration_panel(frame, text, VIDEO_W, VIDEO_H, font_regular)

    # Convert to RGB for moviepy
    return np.array(frame.convert("RGB"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _make_slide(
    section: dict[str, Any],
    logo_map: dict[str, str],
    duration: float,
    section_index: int,
    total_sections: int,
) -> Any:
    """Build one slide as an ImageClip with optional audio."""
    frame_arr = _render_slide_frame(section, logo_map, section_index, total_sections)

    clip = ImageClip(frame_arr, duration=duration)
    clip = clip.with_effects([vfx.FadeIn(FADE_DURATION), vfx.FadeOut(FADE_DURATION)])

    audio_path = section.get("audio_path", "")
    if audio_path and os.path.exists(audio_path):
        try:
            audio = AudioFileClip(audio_path).subclipped(0, duration)
            clip = clip.with_audio(audio)
        except Exception as e:
            print(f"    [VIDEO] Audio attachment failed: {e}")

    return clip


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
    total = len(sections)
    slides = []
    for idx, section in enumerate(sections):
        duration = max(
            MIN_SLIDE_DURATION,
            section.get("audio_duration", MIN_SLIDE_DURATION),
        )
        print(f"  [VIDEO] Building slide {idx + 1}/{total}: {section['title']!r} ({duration:.1f}s)")
        slide = _make_slide(section, logo_map, duration, idx, total)
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
        logger=None,
        ffmpeg_params=["-preset", "ultrafast", "-crf", "26"],
        threads=4,
    )
    print(f"  [VIDEO] Done → {out_path}")
    return out_path
