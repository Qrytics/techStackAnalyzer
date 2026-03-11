# techStackAnalyzer

A CLI tool that accepts any public GitHub repo URL and performs a **deep tech stack analysis**, then produces a **narrated explainer video** as output.

---

## Features

| Capability | Details |
|---|---|
| **Stack Detection** | Languages, package managers, databases, CI/CD, containers, auth, messaging, cloud SDKs |
| **Script Generation** | Engaging, spoken-word narration split into 8 thematic sections |
| **AI Enhancement** | Optional [Ollama](https://ollama.com) LLM (free, local) to rewrite scripts into richer prose |
| **Text-to-Speech** | Per-section MP3 clips via `edge-tts` (falls back to `gTTS`) |
| **Image Gathering** | Tech logos via Devicon CDN → SimpleIcons → Clearbit → coloured placeholder; **parallel downloads** for speed |
| **Video Generation** | PIL-rendered slides with gradient backgrounds, logo grids, and section counters; `libx264 ultrafast` encoding |
| **Reports** | Terminal table + `stack_report.json` |

---

## Slide Design

Each slide features:
- **Dark gradient background** with subtle grid overlay
- **Large bold title** (Lato font) with a unique colour-accented underline per section
- **Section counter pill** (e.g. `2 / 8`) in the top-right corner
- **Tech logo grid** (up to 8 logos, 2 rows of 4, with drop shadows and card outlines)
- **Narration panel** at the bottom with the spoken text
- **Branding watermark** in the corner

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
| `--use-ollama` | Enhance scripts with a locally-running Ollama model (see below). Falls back to templates if Ollama is unavailable. |
| `--ollama-model MODEL` | Ollama model to use (default: `llama3`). Only used with `--use-ollama`. |

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

# Use Ollama to generate richer narration scripts
python analyze.py analyze https://github.com/tiangolo/fastapi --use-ollama

# Use a specific Ollama model
python analyze.py analyze https://github.com/tiangolo/fastapi --use-ollama --ollama-model mistral
```

---

## AI-Enhanced Scripts with Ollama (Free & Local)

Pass `--use-ollama` to have a locally-running [Ollama](https://ollama.com) model rewrite each narration section into more engaging, conversational prose — like a knowledgeable friend explaining the project.

1. **Install Ollama**: https://ollama.com/download
2. **Pull a model**: `ollama pull llama3` (or `mistral`, `phi3`, etc.)
3. **Run the analyzer**: `python analyze.py analyze <URL> --use-ollama`

If Ollama is not installed or not running, the tool falls back to its built-in template narration automatically.

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
  script_generator.py       ← Natural-language narration script (+ Ollama enhancement)
  tts.py                    ← Text-to-speech (edge-tts / gTTS)
  image_gatherer.py         ← Logo fetching (Devicon / SimpleIcons / Clearbit / placeholder)
  video_generator.py        ← PIL slide renderer + moviepy assembly & ultrafast export
  reporter.py               ← Rich terminal table + JSON report
  utils.py                  ← Shared font & slugify helpers
requirements.txt
```

---

## Rate Limits

Without a token the GitHub API allows 60 unauthenticated requests per hour.  For any repository with more than ~50 files you should provide a personal access token (`--token` or `GITHUB_TOKEN`).  The tool will warn you if it encounters rate-limit errors.

---

## License

MIT
