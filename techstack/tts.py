"""
tts.py — Text-to-speech conversion.

Generates one MP3 file per narration section.
Uses edge-tts (async, high quality) with gTTS as a fallback.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any


def _slugify(text: str) -> str:
    """Convert a section title to a safe filename component."""
    import re
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


async def _edge_tts_generate(text: str, output_path: str, voice: str = "en-US-AriaNeural") -> None:
    """Generate speech with edge-tts (async)."""
    import edge_tts  # type: ignore[import]
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _gtts_generate(text: str, output_path: str) -> None:
    """Generate speech with gTTS (fallback)."""
    from gtts import gTTS  # type: ignore[import]
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(output_path)


def generate_audio_clips(
    sections: list[dict[str, Any]],
    output_dir: str | Path,
    voice: str = "en-US-AriaNeural",
) -> list[dict[str, Any]]:
    """
    Convert each narration section to an MP3 file.

    Returns the original section list augmented with:
        - "audio_path"   : absolute path to the MP3
        - "audio_duration": duration in seconds (approximated from text length)

    Parameters
    ----------
    sections   : list returned by script_generator.generate()
    output_dir : directory in which to write MP3 files
    voice      : edge-tts voice name (ignored when falling back to gTTS)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    augmented: list[dict[str, Any]] = []
    for i, section in enumerate(sections):
        title_slug = _slugify(section["title"])
        filename = f"{i:02d}_{title_slug}.mp3"
        mp3_path = str(out / filename)

        text = section["text"]
        print(f"  [TTS] Generating audio for section: {section['title']!r}")

        try:
            # Try edge-tts first
            asyncio.run(_edge_tts_generate(text, mp3_path, voice=voice))
            print(f"        → edge-tts → {mp3_path}")
        except Exception as e_edge:
            print(f"        edge-tts failed ({e_edge}), falling back to gTTS …")
            try:
                _gtts_generate(text, mp3_path)
                print(f"        → gTTS → {mp3_path}")
            except Exception as e_gtts:
                print(f"        gTTS also failed ({e_gtts}). Section will have no audio.")
                mp3_path = ""

        # Approximate duration: ~150 words/min speaking rate
        word_count = len(text.split())
        approx_duration = max(2.0, word_count / 150 * 60)

        augmented.append({
            **section,
            "audio_path": mp3_path,
            "audio_duration": approx_duration,
        })

    return augmented


def merge_audio_clips(
    section_clips: list[dict[str, Any]],
    output_path: str | Path,
) -> str:
    """
    Concatenate all per-section MP3s into one master narration file.

    Returns the path to the merged MP3.
    """
    from pydub import AudioSegment  # type: ignore[import]

    merged = AudioSegment.empty()
    for section in section_clips:
        mp3 = section.get("audio_path", "")
        if mp3 and os.path.exists(mp3):
            merged += AudioSegment.from_mp3(mp3)

    if len(merged) == 0:
        print("  [TTS] No valid audio clips to merge — skipping narration.mp3")
        return ""

    out_path = str(output_path)
    merged.export(out_path, format="mp3")
    print(f"  [TTS] Merged narration saved → {out_path}")
    return out_path
