# techStackAnalyzer

A CLI tool that accepts any public GitHub repo URL and performs a **deep tech stack analysis**. By default it prints a rich terminal table — no audio or video generated unless you ask for them.

---

## Features

| Capability | Details |
|---|---|
| **Stack Detection** | Languages, package managers, databases, CI/CD, containers, auth, messaging, cloud SDKs |
| **Rich Terminal Output** | Formatted summary table printed instantly (default) |
| **JSON Report** | Machine-readable `stack_report.json` saved alongside the table |
| **Script Generation** | Engaging, conversational narration split into 8 thematic sections |
| **AI Enhancement** | Optional [Ollama](https://ollama.com) LLM (free, local) to rewrite scripts into richer prose |
| **Audio Narration** | Per-section MP3 clips via `edge-tts` (falls back to `gTTS`) — opt-in with `--audio` |
| **Explainer Video** | PIL-rendered slides with gradient backgrounds, logo grids, and section counters — opt-in with `--video` |
| **Image Pipeline** | Devicon CDN → SimpleIcons → Clearbit → placeholder; parallel downloads |

---

## Slide Design

Each video slide features:
- **Dark gradient background** with subtle grid overlay
- **Large Lato bold title** with a unique colour-accented underline per section
- **Section counter pill** (e.g. `2 / 8`) in the top-right corner
- **Tech logo grid** (up to 8 logos, 4×2, with drop shadows)
- **Narration panel** at the bottom with the spoken text

---

## Installation

```bash
pip install .
```

> **Prerequisites (for `--video` only)**
> - `ffmpeg` on your `$PATH` — `sudo apt install ffmpeg` / `brew install ffmpeg`

---

## Usage

```
techstack [REPO_URL] [options]
```

`REPO_URL` is **optional**. When omitted, `techstack` reads the `origin` remote of
the git repository in the current directory and derives the GitHub URL automatically.
This works for both HTTPS remotes (`https://github.com/user/repo`) and SSH remotes
(`git@github.com:user/repo.git`).

```bash
# cd into any local GitHub clone and just run:
cd ~/projects/my-app   # a git clone of a GitHub repo
techstack
```

### Options

| Flag | Short | Description |
|---|---|---|
| `--token TOKEN` | `-t` | GitHub personal access token. Raises rate limit 60 → 5,000 req/h. Also via `GITHUB_TOKEN` env var. |
| `--output DIR` | `-o` | Base output directory (default: current directory). |
| `--audio` | `-a` | Generate TTS audio narration (MP3). |
| `--video` | `-v` | Generate explainer video (MP4). Implies `--audio`. |
| `--voice VOICE` | | `edge-tts` voice (default: `en-US-AriaNeural`). Run `edge-tts --list-voices` to browse. |
| `--use-ollama` | | Use a local Ollama LLM to enhance scripts (see below). Falls back gracefully if unavailable. |
| `--ollama-model MODEL` | | Ollama model to use (default: `llama3`). Only used with `--use-ollama`. |

### Examples

```bash
# Auto-detect from local git clone (no URL needed)
cd ~/projects/my-app
techstack

# Explicit URL — instant text analysis (default — fastest)
techstack https://github.com/tiangolo/fastapi

# With a GitHub token to avoid rate limits
techstack https://github.com/vercel/next.js -t ghp_xxxxxxxxxxxx

# Text analysis + audio narration
techstack https://github.com/django/django --audio

# Full analysis with explainer video
techstack https://github.com/torvalds/linux --video

# Explainer video with Ollama-enhanced scripts
techstack https://github.com/tiangolo/fastapi --video --use-ollama

# Use a specific Ollama model or remote host
OLLAMA_HOST=http://gpu-box:11434 techstack https://github.com/tiangolo/fastapi --video --use-ollama --ollama-model mistral
```

---

## AI-Enhanced Scripts with Ollama (Free & Local)

Pass `--use-ollama` to have a locally-running [Ollama](https://ollama.com) model rewrite each narration section into more engaging, conversational prose — like a knowledgeable friend explaining the project.

1. **Install Ollama**: https://ollama.com/download
2. **Pull a model**: `ollama pull llama3` (or `mistral`, `phi3`, etc.)
3. **Run the analyzer**: `techstack <URL> --video --use-ollama`

If Ollama is not installed or not running, the tool falls back to its built-in template narration automatically with a single clean log line.

The `OLLAMA_HOST` environment variable can be set to a non-default endpoint (e.g. Docker containers or remote GPU servers).

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
| `OLLAMA_HOST` | Ollama base URL (default: `http://localhost:11434`) |

---

## Architecture

```
techstack/
  cli.py                    ← argparse CLI entry point  (`techstack` command)
  detector.py               ← GitHub API scanning & pattern matching
  script_generator.py       ← Natural-language narration script (+ Ollama enhancement)
  tts.py                    ← Text-to-speech (edge-tts / gTTS)
  image_gatherer.py         ← Logo fetching (Devicon / SimpleIcons / Clearbit / placeholder)
  video_generator.py        ← PIL slide renderer + moviepy ultrafast export
  reporter.py               ← Rich terminal table + JSON report
  utils.py                  ← Shared font & slugify helpers
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
