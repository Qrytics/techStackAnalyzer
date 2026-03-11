# techStackAnalyzer

A CLI tool that accepts any public GitHub repo URL and performs a **deep tech stack analysis**, then produces a **narrated explainer video** as output.

---

## Features

| Capability | Details |
|---|---|
| **Stack Detection** | Languages, package managers, databases, CI/CD, containers, auth, messaging, cloud SDKs |
| **Script Generation** | Structured, spoken-word narration split into sections |
| **Text-to-Speech** | Per-section MP3 clips via `edge-tts` (falls back to `gTTS`) |
| **Image Gathering** | Tech logos via Clearbit → Wikimedia → coloured placeholder |
| **Video Generation** | `moviepy`-assembled `.mp4` with slide transitions and audio sync |
| **Reports** | Terminal table + `stack_report.json` |

---

## Installation

### Prerequisites

- Python 3.10+
- `ffmpeg` installed and on your `$PATH` (required by moviepy)
  ```bash
  # Ubuntu / Debian
  sudo apt install ffmpeg

  # macOS (Homebrew)
  brew install ffmpeg

  # Windows — download from https://ffmpeg.org/download.html
  ```
- (Optional) ImageMagick — required for `TextClip` in moviepy on Linux/macOS
  ```bash
  sudo apt install imagemagick   # Ubuntu/Debian
  brew install imagemagick       # macOS
  ```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

```
python analyze.py analyze <GITHUB_REPO_URL> [options]
```

### Options

| Flag | Description |
|---|---|
| `--token / -t TOKEN` | GitHub personal access token. Raises rate limit from 60 → 5 000 req/h. Can also be set via `GITHUB_TOKEN` env var. |
| `--output / -o DIR` | Base output directory (default: current directory). |
| `--skip-video` | Skip image gathering and video generation. |
| `--skip-audio` | Skip TTS audio generation. |
| `--voice VOICE` | `edge-tts` voice (default: `en-US-AriaNeural`). Run `edge-tts --list-voices` to browse. |

### Examples

```bash
# Full analysis with video
python analyze.py analyze https://github.com/tiangolo/fastapi

# With a GitHub token (recommended)
python analyze.py analyze https://github.com/vercel/next.js --token ghp_xxxxxxxxxxxx

# Report + audio only (no video)
python analyze.py analyze https://github.com/django/django --skip-video

# Report only (no audio or video)
python analyze.py analyze https://github.com/torvalds/linux --skip-audio --skip-video
```

---

## Output

After running the command you will find a folder named after the repository slug in the current directory (or the directory specified by `--output`):

```
fastapi/
├── stack_report.json      # Full machine-readable analysis
├── narration.mp3          # Merged narration audio
├── fastapi.mp4            # Explainer video
└── audio/
│   ├── 00_overview.mp3
│   ├── 01_languages_frameworks.mp3
│   └── …
└── logos/
    ├── python.png
    ├── fastapi.png
    └── …
```

A formatted summary table is also printed to the terminal.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (alternative to `--token`) |

---

## Architecture

```
analyze.py                  ← argparse CLI entry point
techstack/
  detector.py               ← GitHub API scanning & pattern matching
  script_generator.py       ← Natural-language narration script
  tts.py                    ← Text-to-speech (edge-tts / gTTS)
  image_gatherer.py         ← Logo fetching (Clearbit / Wikimedia / placeholder)
  video_generator.py        ← moviepy slide assembly & export
  reporter.py               ← Rich terminal table + JSON report
requirements.txt
```

---

## Rate Limits

Without a token the GitHub API allows 60 unauthenticated requests per hour.  For any repository with more than ~50 files you should provide a personal access token (`--token` or `GITHUB_TOKEN`).  The tool will warn you if it encounters rate-limit errors.

---

## License

MIT
