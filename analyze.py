#!/usr/bin/env python3
"""
analyze.py — Tech Stack Analyzer CLI entry point.

Usage:
    python analyze.py analyze <github-repo-url> [options]

Example:
    python analyze.py analyze https://github.com/tiangolo/fastapi
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _build_output_dir(repo_url: str, base: str = ".") -> Path:
    """Return an output directory path derived from the repo slug."""
    m = re.search(r"github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", repo_url)
    slug = _slugify(m.group(1)) if m else "output"
    out = Path(base) / slug
    out.mkdir(parents=True, exist_ok=True)
    return out


def cmd_analyze(args: argparse.Namespace) -> None:
    """Handle the 'analyze' sub-command."""
    repo_url: str = args.repo_url
    github_token: str | None = args.token or os.environ.get("GITHUB_TOKEN")
    output_base: str = args.output or "."
    skip_video: bool = args.skip_video
    skip_audio: bool = args.skip_audio
    voice: str = args.voice

    print(f"\n🔍 Analyzing: {repo_url}\n")

    # ---------------------------------------------------------------
    # 1. Tech stack detection
    # ---------------------------------------------------------------
    print("── Step 1/5  Stack Detection ────────────────────────────────")
    from techstack.detector import detect

    try:
        stack = detect(repo_url, github_token=github_token)
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] Detection failed: {exc}", file=sys.stderr)
        raise

    # ---------------------------------------------------------------
    # 2. Print terminal table + save JSON report
    # ---------------------------------------------------------------
    print("\n── Step 2/5  Report Generation ──────────────────────────────")
    from techstack.reporter import print_summary_table, save_json_report

    print_summary_table(stack)

    out_dir = _build_output_dir(repo_url, base=output_base)
    json_path = save_json_report(stack, out_dir / "stack_report.json")

    # ---------------------------------------------------------------
    # 3. Script generation
    # ---------------------------------------------------------------
    print("\n── Step 3/5  Script Generation ──────────────────────────────")
    from techstack.script_generator import generate

    sections = generate(stack)
    for s in sections:
        print(f"   • {s['title']} ({len(s['text'].split())} words)")

    # ---------------------------------------------------------------
    # 4. Text-to-speech
    # ---------------------------------------------------------------
    if not skip_audio:
        print("\n── Step 4/5  Text-to-Speech ──────────────────────────────────")
        from techstack.tts import generate_audio_clips, merge_audio_clips

        audio_dir = out_dir / "audio"
        sections = generate_audio_clips(sections, audio_dir, voice=voice)
        narration_mp3 = merge_audio_clips(sections, out_dir / "narration.mp3")
        if narration_mp3:
            print(f"  Narration MP3 → {narration_mp3}")
    else:
        print("\n── Step 4/5  Text-to-Speech (skipped) ───────────────────────")
        for s in sections:
            s["audio_path"] = ""
            s["audio_duration"] = len(s["text"].split()) / 150 * 60

    # ---------------------------------------------------------------
    # 5. Image gathering + video generation
    # ---------------------------------------------------------------
    if not skip_video:
        print("\n── Step 5/5  Image Gathering ─────────────────────────────────")
        from techstack.image_gatherer import fetch_logos

        all_techs: list[str] = []
        for s in sections:
            for t in s.get("techs", []):
                if t not in all_techs:
                    all_techs.append(t)

        logo_map = fetch_logos(all_techs, out_dir)

        print("\n── Step 5/5  Video Generation ────────────────────────────────")
        from techstack.video_generator import generate_video

        m = re.search(r"github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", repo_url)
        repo_slug = _slugify(m.group(1)) if m else "output"
        video_path = out_dir / f"{repo_slug}.mp4"

        try:
            generate_video(sections, logo_map, video_path)
        except Exception as exc:
            print(f"  [WARNING] Video generation failed: {exc}")
            print("  The analysis report and audio are still available.")
    else:
        print("\n── Step 5/5  Video Generation (skipped) ─────────────────────")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------
    print(f"\n✅ Analysis complete!  Output folder → {out_dir.resolve()}\n")
    print("   Files:")
    for f in sorted(out_dir.rglob("*")):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"     {f.relative_to(out_dir)}  ({size_kb:.1f} KB)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analyze",
        description="Tech Stack Analyzer — deep-dive a public GitHub repo and produce an explainer video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze.py analyze https://github.com/tiangolo/fastapi
  python analyze.py analyze https://github.com/torvalds/linux --skip-video
  python analyze.py analyze https://github.com/vercel/next.js --token ghp_xxx
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    analyze_parser = sub.add_parser(
        "analyze",
        help="Analyze a public GitHub repository",
    )
    analyze_parser.add_argument(
        "repo_url",
        metavar="REPO_URL",
        help="Full GitHub repository URL (e.g. https://github.com/user/repo)",
    )
    analyze_parser.add_argument(
        "--token", "-t",
        metavar="GITHUB_TOKEN",
        default=None,
        help="GitHub personal access token (or set GITHUB_TOKEN env var). "
             "Raises API rate limit from 60 to 5000 req/h.",
    )
    analyze_parser.add_argument(
        "--output", "-o",
        metavar="DIR",
        default=".",
        help="Base directory for output folder (default: current directory).",
    )
    analyze_parser.add_argument(
        "--skip-video",
        action="store_true",
        default=False,
        help="Skip image gathering and video generation.",
    )
    analyze_parser.add_argument(
        "--skip-audio",
        action="store_true",
        default=False,
        help="Skip TTS audio generation (implies --skip-video unless --no-skip-video is set).",
    )
    analyze_parser.add_argument(
        "--voice",
        metavar="VOICE",
        default="en-US-AriaNeural",
        help="edge-tts voice name (default: en-US-AriaNeural). "
             "Run `edge-tts --list-voices` to see available voices.",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
