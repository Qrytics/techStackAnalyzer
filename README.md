# techStackAnalyzer

A CLI tool that accepts any public GitHub repo URL and performs a **deep tech stack analysis**. By default it prints a rich terminal table — no audio or video generated unless you ask for them.

---

## Features

| Capability | Details |
|---|---|
| **Stack Detection** | Languages, package managers, databases, CI/CD, containers, auth, messaging, cloud SDKs |
| **Rich Terminal Output** | Formatted summary table printed instantly (default) |
| **JSON Report** | Machine-readable `stack_report.json` saved alongside the table |
| **Audio Narration** | Per-section MP3 clips via `edge-tts` (falls back to `gTTS`) — opt-in with `--audio` |
| **Explainer Video** | `moviepy`-assembled `.mp4` with slide transitions — opt-in with `--video` |

---

## Installation

```bash
pip install .
```

> **Prerequisites (for `--video` only)**
> - `ffmpeg` on your `$PATH` — `sudo apt install ffmpeg` / `brew install ffmpeg`
> - ImageMagick — `sudo apt install imagemagick` / `brew install imagemagick`

---

## Usage

```
techstack <REPO_URL> [options]
```

### Options

| Flag | Short | Description |
|---|---|---|
| `--token TOKEN` | `-t` | GitHub personal access token. Raises rate limit 60 → 5,000 req/h. Also via `GITHUB_TOKEN` env var. |
| `--output DIR` | `-o` | Base output directory (default: current directory). |
| `--audio` | `-a` | Generate TTS audio narration (MP3). |
| `--video` | `-v` | Generate explainer video (MP4). Implies `--audio`. |
| `--voice VOICE` | | `edge-tts` voice (default: `en-US-AriaNeural`). Run `edge-tts --list-voices` to browse. |

### Examples

```bash
# Instant text analysis (default — fastest)
techstack https://github.com/tiangolo/fastapi

# With a GitHub token to avoid rate limits
techstack https://github.com/vercel/next.js -t ghp_xxxxxxxxxxxx

# Text analysis + audio narration
techstack https://github.com/django/django --audio

# Full analysis with explainer video
techstack https://github.com/torvalds/linux --video
```

---

## Output

**Default (text only):**

A formatted summary is printed to the terminal and `stack_report.json` is saved in a folder named after the repo slug.

**With `--audio` or `--video`:**

```
fastapi/
├── stack_report.json      # Full machine-readable analysis
├── narration.mp3          # Merged narration (--audio / --video)
├── fastapi.mp4            # Explainer video (--video only)
├── audio/
│   ├── 00_overview.mp3
│   ├── 01_languages_frameworks.mp3
│   └── …
└── logos/
    ├── python.png
    ├── fastapi.png
    └── …
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (alternative to `-t`) |

---

## Architecture

```
techstack/
  cli.py                    ← argparse CLI entry point  (`techstack` command)
  detector.py               ← GitHub API scanning & pattern matching
  script_generator.py       ← Natural-language narration script
  tts.py                    ← Text-to-speech (edge-tts / gTTS)
  image_gatherer.py         ← Logo fetching (Clearbit / Wikimedia / placeholder)
  video_generator.py        ← moviepy slide assembly & export
  reporter.py               ← Rich terminal table + JSON report
analyze.py                  ← legacy shim (delegates to techstack.cli)
pyproject.toml              ← pip-installable package config
requirements.txt            ← raw dependency list
```

---

## Rate Limits

Without a token the GitHub API allows 60 unauthenticated requests per hour. For repositories with more than ~50 files provide a personal access token (`-t` / `GITHUB_TOKEN`).

---

## License

MIT
