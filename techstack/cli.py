#!/usr/bin/env python3
"""
techstack CLI entry point.

Usage:
    techstack [REPO_URL] [options]

When run inside a local git clone the REPO_URL argument is optional —
techstack will read the 'origin' remote and derive the GitHub URL automatically.

Examples:
    techstack                                          # inside a git clone
    techstack https://github.com/tiangolo/fastapi
    techstack https://github.com/vercel/next.js -t ghp_xxx
    techstack https://github.com/django/django --audio
    techstack https://github.com/torvalds/linux --video
    techstack https://github.com/tiangolo/fastapi --video --use-ollama
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
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


def _get_github_url_from_git_remote() -> str | None:
    """Return a GitHub HTTPS URL derived from the local git 'origin' remote.

    Returns *None* if the current directory is not inside a git repository or
    the remote URL does not point to GitHub.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    raw = result.stdout.strip()
    if not raw:
        return None

    # SSH format: git@github.com:user/repo.git  →  https://github.com/user/repo
    ssh_match = re.match(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?$", raw)
    if ssh_match:
        return f"https://github.com/{ssh_match.group(1)}"

    # HTTPS format: https://github.com/user/repo(.git)
    https_match = re.match(r"(https://github\.com/[^/]+/[^/]+?)(?:\.git)?/?$", raw)
    if https_match:
        return https_match.group(1)

    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="techstack",
        description=(
            "Tech Stack Analyzer — analyze any public GitHub repo and display its tech stack.\n\n"
            "When run inside a local git clone the REPO_URL argument is optional;\n"
            "techstack will read the 'origin' remote automatically."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  techstack                                        # inside a git clone — URL auto-detected
  techstack https://github.com/tiangolo/fastapi
  techstack https://github.com/vercel/next.js -t ghp_xxxxxxxxxxxx
  techstack https://github.com/django/django --audio
  techstack https://github.com/torvalds/linux --video
  techstack https://github.com/tiangolo/fastapi --video --use-ollama
        """,
    )

    parser.add_argument(
        "repo_url",
        metavar="REPO_URL",
        nargs="?",
        default=None,
        help=(
            "Full GitHub repository URL (e.g. https://github.com/user/repo). "
            "If omitted, the URL is read from the 'origin' remote of the current git repository."
        ),
    )
    parser.add_argument(
        "--token", "-t",
        metavar="TOKEN",
        default=None,
        help="GitHub personal access token (or set GITHUB_TOKEN env var). "
             "Raises API rate limit from 60 to 5,000 req/h.",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="DIR",
        default=".",
        help="Base directory for output (default: current directory).",
    )
    parser.add_argument(
        "--audio", "-a",
        action="store_true",
        default=False,
        help="Generate TTS audio narration (MP3).",
    )
    parser.add_argument(
        "--video", "-v",
        action="store_true",
        default=False,
        help="Generate explainer video (MP4). Implies --audio.",
    )
    parser.add_argument(
        "--voice",
        metavar="VOICE",
        default="en-US-AriaNeural",
        help="edge-tts voice (default: en-US-AriaNeural). "
             "Run `edge-tts --list-voices` to browse options.",
    )
    parser.add_argument(
        "--use-ollama",
        action="store_true",
        default=False,
        help="Use a locally-running Ollama model to enhance the generated scripts. "
             "Requires Ollama to be installed and running (https://ollama.com). "
             "Falls back to template text if Ollama is unavailable.",
    )
    parser.add_argument(
        "--ollama-model",
        metavar="MODEL",
        default="llama3",
        help="Ollama model to use for script enhancement (default: llama3). "
             "Only used when --use-ollama is set.",
    )

    args = parser.parse_args()

    repo_url: str | None = args.repo_url
    if repo_url is None:
        repo_url = _get_github_url_from_git_remote()
        if repo_url is None:
            parser.error(
                "REPO_URL was not provided and could not be detected from a git remote.\n"
                "Either supply a URL explicitly or run techstack from inside a GitHub repository clone."
            )
        print(f"ℹ️  Using remote origin URL: {repo_url}")

    github_token: str | None = args.token or os.environ.get("GITHUB_TOKEN")
    output_base: str = args.output
    want_audio: bool = args.audio or args.video
    want_video: bool = args.video
    voice: str = args.voice
    use_ollama: bool = args.use_ollama
    ollama_model: str = args.ollama_model

    print(f"\n🔍 Analyzing: {repo_url}\n")

    # ---------------------------------------------------------------
    # Step 1 – Tech stack detection
    # ---------------------------------------------------------------
    print("── Step 1  Stack Detection ──────────────────────────────────")
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
    # Step 2 – Print terminal table + save JSON report
    # ---------------------------------------------------------------
    print("\n── Step 2  Report ───────────────────────────────────────────")
    from techstack.reporter import print_summary_table, save_json_report

    print_summary_table(stack)

    out_dir = _build_output_dir(repo_url, base=output_base)
    save_json_report(stack, out_dir / "stack_report.json")

    # In text-only mode we are done — exit here for minimum latency.
    if not want_audio and not want_video:
        print(f"\n✅ Done!  Report saved → {out_dir.resolve() / 'stack_report.json'}\n")
        return

    # ---------------------------------------------------------------
    # Step 3 – Script generation (needed for audio/video)
    # ---------------------------------------------------------------
    print("\n── Step 3  Script Generation ────────────────────────────────")
    from techstack.script_generator import generate

    sections = generate(stack, use_ollama=use_ollama, ollama_model=ollama_model)
    for s in sections:
        print(f"   • {s['title']} ({len(s['text'].split())} words)")

    # ---------------------------------------------------------------
    # Step 4 – Text-to-speech
    # ---------------------------------------------------------------
    print("\n── Step 4  Text-to-Speech ───────────────────────────────────")
    from techstack.tts import generate_audio_clips, merge_audio_clips

    audio_dir = out_dir / "audio"
    sections = generate_audio_clips(sections, audio_dir, voice=voice)
    narration_mp3 = merge_audio_clips(sections, out_dir / "narration.mp3")
    if narration_mp3:
        print(f"  Narration MP3 → {narration_mp3}")

    if not want_video:
        print(f"\n✅ Done!  Output folder → {out_dir.resolve()}\n")
        _list_output(out_dir)
        return

    # ---------------------------------------------------------------
    # Step 5 – Image gathering + video generation
    # ---------------------------------------------------------------
    print("\n── Step 5  Image Gathering ──────────────────────────────────")
    from techstack.image_gatherer import fetch_logos

    all_techs: list[str] = []
    for s in sections:
        for t in s.get("techs", []):
            if t not in all_techs:
                all_techs.append(t)

    logo_map = fetch_logos(all_techs, out_dir)

    print("\n── Step 6  Video Generation ─────────────────────────────────")
    from techstack.video_generator import generate_video

    m = re.search(r"github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", repo_url)
    repo_slug = _slugify(m.group(1)) if m else "output"
    video_path = out_dir / f"{repo_slug}.mp4"

    try:
        generate_video(sections, logo_map, video_path)
    except Exception as exc:
        print(f"  [WARNING] Video generation failed: {exc}")
        print("  The analysis report and audio are still available.")

    print(f"\n✅ Done!  Output folder → {out_dir.resolve()}\n")
    _list_output(out_dir)


def _list_output(out_dir: Path) -> None:
    """Print a short listing of files in the output directory."""
    print("   Files:")
    for f in sorted(out_dir.rglob("*")):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"     {f.relative_to(out_dir)}  ({size_kb:.1f} KB)")
    print()


if __name__ == "__main__":
    main()
