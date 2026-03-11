"""
image_gatherer.py — Fetch logos and illustrations for detected technologies.

Strategy (in priority order):
  1. Devicon CDN      — https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/…
  2. SimpleIcons CDN  — https://cdn.simpleicons.org/{slug}/FFFFFF (white SVG → PNG)
  3. Clearbit Logo API — https://logo.clearbit.com/{domain}
  4. Simple coloured placeholder image (always succeeds)

Downloads are performed in parallel for faster Step-5 execution.
"""

from __future__ import annotations

import io
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

from techstack.utils import find_system_font, slugify

# ---------------------------------------------------------------------------
# Devicon slug map — maps technology label → devicon icon slug
# ---------------------------------------------------------------------------
DEVICON_SLUGS: dict[str, str] = {
    # Languages
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Go": "go",
    "Rust": "rust",
    "Java": "java",
    "Kotlin": "kotlin",
    "Ruby": "ruby",
    "PHP": "php",
    "C#": "csharp",
    "C++": "cplusplus",
    "C": "c",
    "Swift": "swift",
    "Scala": "scala",
    "Elixir": "elixir",
    "Haskell": "haskell",
    "Dart": "dart",
    "Lua": "lua",
    "R": "r",
    "Shell": "bash",
    "PowerShell": "powershell",
    # Frameworks / Libraries
    "FastAPI": "fastapi",
    "Flask": "flask",
    "Django": "django",
    "Express.js": "express",
    "NestJS": "nestjs",
    "Next.js": "nextjs",
    "Nuxt.js": "nuxtjs",
    "Vue.js": "vuejs",
    "React": "react",
    "Angular": "angularjs",
    "Svelte": "svelte",
    "SvelteKit / Svelte": "svelte",
    "Spring Boot": "spring",
    "Ruby on Rails": "rails",
    "Laravel": "laravel",
    "Gin (Go)": "go",
    "Echo (Go)": "go",
    "Actix-web (Rust)": "rust",
    "Axum / Tokio (Rust)": "rust",
    "Phoenix (Elixir)": "elixir",
    # Databases
    "PostgreSQL": "postgresql",
    "MySQL": "mysql",
    "MySQL / MariaDB": "mysql",
    "MariaDB": "mariadb",
    "MongoDB": "mongodb",
    "Redis": "redis",
    "SQLite": "sqlite",
    "Elasticsearch": "elasticsearch",
    "Cassandra": "cassandra",
    "CouchDB": "couchdb",
    "Firebase / Firestore": "firebase",
    "Supabase": "supabase",
    "Neo4j": "neo4j",
    # ORMs / Data tools
    "Prisma ORM": "prisma",
    "SQLAlchemy / Alembic": "sqlalchemy",
    "Sequelize ORM": "sequelize",
    "Django ORM": "django",
    # Auth
    "GitHub Actions": "github",
    "Auth0": "auth0",
    # CI/CD
    "CircleCI": "circleci",
    "Jenkins": "jenkins",
    "GitLab CI": "gitlab",
    "Travis CI": "travis",
    "Azure Pipelines": "azure",
    # Containers / Orchestration
    "Docker": "docker",
    "Docker Compose": "docker",
    "Kubernetes": "kubernetes",
    "Helm": "helm",
    # IaC / Cloud tools
    "Terraform": "terraform",
    "Ansible": "ansible",
    "Pulumi": "pulumi",
    # Cloud
    "AWS": "amazonwebservices",
    "Google Cloud": "googlecloud",
    "Azure": "azure",
    "DigitalOcean": "digitalocean",
    "Cloudflare": "cloudflare",
    "Vercel": "vercel",
    "Netlify": "netlify",
    "Heroku": "heroku",
    # Other
    "GraphQL": "graphql",
    "Apache Kafka": "apachekafka",
    "Nginx": "nginx",
    "Apache": "apache",
    "Linux": "linux",
    "Ubuntu": "ubuntu",
    "Debian": "debian",
    "Git": "git",
    "GitHub": "github",
    "GitLab": "gitlab",
    "Bitbucket": "bitbucket",
    "Node.js / npm": "nodejs",
    "Node.js / Yarn": "yarn",
    "Node.js / pnpm": "pnpm",
    "Python / pip": "python",
    "Python / pipenv": "python",
    "Python / Poetry or PEP-517": "python",
    "Rust / Cargo": "rust",
    "Go Modules": "go",
    "Java / Maven": "maven",
    "Java / Gradle": "gradle",
    "Kotlin / Gradle": "gradle",
    "Ruby / Bundler": "ruby",
    "PHP / Composer": "composer",
    "Dart / Flutter": "flutter",
    "Elixir / Mix": "elixir",
}

# ---------------------------------------------------------------------------
# SimpleIcons slug map — fallback for items not in Devicon
# ---------------------------------------------------------------------------
SIMPLEICONS_SLUGS: dict[str, str] = {
    "JWT": "jsonwebtokens",
    "OAuth": "oauth",
    "Okta": "okta",
    "Keycloak": "keycloak",
    "NextAuth.js": "nextdotjs",
    "Passport.js": "passport",
    "RabbitMQ": "rabbitmq",
    "Celery": "celery",
    "NATS": "natsdotio",
    "AWS SQS/SNS": "amazonsqs",
    "Google Pub/Sub": "googlepubsub",
    "DynamoDB": "amazondynamodb",
    "PlanetScale": "planetscale",
    "InfluxDB": "influxdb",
    "CockroachDB": "cockroachlabs",
    "Supabase Auth": "supabase",
    "Firebase Auth": "firebase",
    "AWS CDK": "amazonaws",
    "Serverless Framework": "serverless",
    "Fly.io": "flyio",
}

# ---------------------------------------------------------------------------
# Clearbit domain map — final fallback for logo images
# ---------------------------------------------------------------------------
TECH_DOMAINS: dict[str, str] = {
    "Python": "python.org",
    "JavaScript": "javascript.info",
    "TypeScript": "typescriptlang.org",
    "Go": "go.dev",
    "Rust": "rust-lang.org",
    "Java": "java.com",
    "Kotlin": "kotlinlang.org",
    "Ruby": "ruby-lang.org",
    "PHP": "php.net",
    "C#": "microsoft.com",
    "Swift": "swift.org",
    "Scala": "scala-lang.org",
    "Elixir": "elixir-lang.org",
    "Haskell": "haskell.org",
    "Dart": "dart.dev",
    "FastAPI": "fastapi.tiangolo.com",
    "Flask": "flask.palletsprojects.com",
    "Django": "djangoproject.com",
    "Express.js": "expressjs.com",
    "NestJS": "nestjs.com",
    "Next.js": "nextjs.org",
    "Nuxt.js": "nuxt.com",
    "Vue.js": "vuejs.org",
    "React": "reactjs.org",
    "Angular": "angular.io",
    "Svelte": "svelte.dev",
    "SvelteKit / Svelte": "svelte.dev",
    "Spring Boot": "spring.io",
    "Ruby on Rails": "rubyonrails.org",
    "Laravel": "laravel.com",
    "PostgreSQL": "postgresql.org",
    "MySQL": "mysql.com",
    "MySQL / MariaDB": "mysql.com",
    "MongoDB": "mongodb.com",
    "Redis": "redis.io",
    "SQLite": "sqlite.org",
    "Elasticsearch": "elastic.co",
    "Cassandra": "cassandra.apache.org",
    "DynamoDB": "aws.amazon.com",
    "Firebase / Firestore": "firebase.google.com",
    "Neo4j": "neo4j.com",
    "InfluxDB": "influxdata.com",
    "CockroachDB": "cockroachlabs.com",
    "Supabase": "supabase.com",
    "PlanetScale": "planetscale.com",
    "Prisma ORM": "prisma.io",
    "SQLAlchemy / Alembic": "sqlalchemy.org",
    "TypeORM": "typeorm.io",
    "Sequelize ORM": "sequelize.org",
    "OAuth": "oauth.net",
    "JWT": "jwt.io",
    "Auth0": "auth0.com",
    "Okta": "okta.com",
    "Keycloak": "keycloak.org",
    "NextAuth.js": "next-auth.js.org",
    "Supabase Auth": "supabase.com",
    "Apache Kafka": "kafka.apache.org",
    "RabbitMQ": "rabbitmq.com",
    "Celery": "celeryq.dev",
    "NATS": "nats.io",
    "GitHub Actions": "github.com",
    "CircleCI": "circleci.com",
    "Jenkins": "jenkins.io",
    "GitLab CI": "gitlab.com",
    "Travis CI": "travis-ci.com",
    "Azure Pipelines": "azure.microsoft.com",
    "Docker": "docker.com",
    "Docker Compose": "docker.com",
    "Kubernetes": "kubernetes.io",
    "Helm": "helm.sh",
    "Terraform": "terraform.io",
    "Pulumi": "pulumi.com",
    "Serverless Framework": "serverless.com",
    "AWS CDK": "aws.amazon.com",
    "Ansible": "ansible.com",
    "AWS": "aws.amazon.com",
    "Google Cloud": "cloud.google.com",
    "Azure": "azure.microsoft.com",
    "DigitalOcean": "digitalocean.com",
    "Cloudflare": "cloudflare.com",
    "Vercel": "vercel.com",
    "Netlify": "netlify.com",
    "Heroku": "heroku.com",
    "Fly.io": "fly.io",
}

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "TechStackAnalyzer/1.0 (github.com)"})

_DEVICON_BASE = (
    "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{slug}/{slug}-original.png"
)
_DEVICON_PLAIN_BASE = (
    "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{slug}/{slug}-plain.png"
)
_SIMPLEICONS_BASE = "https://cdn.simpleicons.org/{slug}/FFFFFF"


def _try_download(url: str, dest: Path, timeout: int = 10) -> bool:
    """GET *url* and save to *dest* if the response is an image. Returns True on success."""
    try:
        resp = _SESSION.get(url, timeout=timeout)
        ct = resp.headers.get("content-type", "")
        if resp.status_code == 200 and ("image" in ct or "svg" in ct):
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def _svg_to_png(svg_path: Path, size: int = 256) -> bool:
    """
    Convert an SVG file to PNG using cairosvg if available.

    ``cairosvg`` is an optional dependency — if it is not installed, SVG
    files are kept as-is and the caller falls back to the next source.
    Returns True if conversion succeeded, False otherwise.
    """
    try:
        import cairosvg  # type: ignore[import]  # optional dep
        png_path = svg_path.with_suffix(".png")
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=size,
            output_height=size,
        )
        svg_path.unlink(missing_ok=True)
        return True
    except ImportError:
        return False  # cairosvg not installed — keep SVG and skip
    except (OSError, IOError, Exception):
        return False  # conversion failed for another reason


def _fetch_devicon(tech: str, dest_dir: Path) -> str | None:
    """Try Devicon CDN (original, then plain variant). Returns file path or None."""
    slug = DEVICON_SLUGS.get(tech)
    if not slug:
        return None
    dest = dest_dir / f"{slugify(tech)}.png"
    # Try original colour variant
    for url_tpl in (_DEVICON_BASE, _DEVICON_PLAIN_BASE):
        url = url_tpl.format(slug=slug)
        if _try_download(url, dest):
            return str(dest)
    return None


def _fetch_simpleicons(tech: str, dest_dir: Path) -> str | None:
    """Try SimpleIcons CDN (white SVG, converted to PNG if possible). Returns path or None."""
    slug = SIMPLEICONS_SLUGS.get(tech) or re.sub(r"[^a-z0-9]", "", tech.lower())
    svg_dest = dest_dir / f"{slugify(tech)}.svg"
    if _try_download(_SIMPLEICONS_BASE.format(slug=slug), svg_dest):
        # Try SVG→PNG conversion
        if _svg_to_png(svg_dest):
            return str(svg_dest.with_suffix(".png"))
        # Keep the SVG as-is; moviepy can handle it via PIL
        return str(svg_dest)
    return None


def _fetch_clearbit(tech: str, dest_dir: Path) -> str | None:
    """Try Clearbit Logo API. Returns file path or None."""
    domain = TECH_DOMAINS.get(tech)
    if not domain:
        return None
    dest = dest_dir / f"{slugify(tech)}.png"
    url = f"https://logo.clearbit.com/{domain}?size=256"
    if _try_download(url, dest):
        return str(dest)
    return None


# Palette for placeholders (cycles through a pleasant set)
_PALETTE = [
    ("#4A90D9", "#FFFFFF"),
    ("#E85D4A", "#FFFFFF"),
    ("#2ECC71", "#FFFFFF"),
    ("#9B59B6", "#FFFFFF"),
    ("#F39C12", "#1A1A1A"),
    ("#1ABC9C", "#FFFFFF"),
    ("#E74C3C", "#FFFFFF"),
    ("#3498DB", "#FFFFFF"),
    ("#8E44AD", "#FFFFFF"),
    ("#16A085", "#FFFFFF"),
]


def _make_placeholder(tech: str, dest: Path, index: int = 0) -> str:
    """Create a polished coloured placeholder PNG when no logo is found."""
    bg_hex, text_hex = _PALETTE[index % len(_PALETTE)]

    def _hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    size = 256
    bg_rgb = _hex_to_rgb(bg_hex)
    dark_rgb = tuple(max(0, c - 40) for c in bg_rgb)

    # Gradient background (RGBA)
    img = Image.new("RGBA", (size, size))
    for y in range(size):
        t = y / size
        r = int((1 - t) * bg_rgb[0] + t * dark_rgb[0])
        g = int((1 - t) * bg_rgb[1] + t * dark_rgb[1])
        b = int((1 - t) * bg_rgb[2] + t * dark_rgb[2])
        for x in range(size):
            img.putpixel((x, y), (r, g, b, 255))

    draw = ImageDraw.Draw(img)

    # Rounded border (use solid RGB tuple — RGBA images accept RGBA or RGB outlines)
    text_rgb = _hex_to_rgb(text_hex)
    draw.rounded_rectangle([12, 12, size - 12, size - 12], radius=20,
                            outline=(*text_rgb, 68), width=2)

    label = tech[:18] + ("…" if len(tech) > 18 else "")
    font_path = find_system_font(bold=True)
    try:
        font = ImageFont.truetype(font_path, size=22) if font_path else ImageFont.load_default()
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Center the text
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2
    # Shadow (semi-transparent black: 40% opacity = 102/255)
    _SHADOW_ALPHA = 102
    draw.text((x + 2, y + 2), label, fill=(0, 0, 0, _SHADOW_ALPHA), font=font)
    draw.text((x, y), label, fill=(*text_rgb, 255), font=font)

    img.save(str(dest), "PNG")
    return str(dest)


def _fetch_logo_for_tech(args: tuple[int, str, Path]) -> tuple[str, str, str]:
    """
    Worker function run in thread pool.

    Returns (tech, file_path, source_label).
    """
    index, tech, logo_dir = args

    # 1 – Devicon
    path = _fetch_devicon(tech, logo_dir)
    if path:
        return tech, path, "Devicon"

    # 2 – SimpleIcons
    path = _fetch_simpleicons(tech, logo_dir)
    if path:
        return tech, path, "SimpleIcons"

    # 3 – Clearbit
    path = _fetch_clearbit(tech, logo_dir)
    if path:
        return tech, path, "Clearbit"

    # 4 – Placeholder (always succeeds)
    dest = logo_dir / f"{slugify(tech)}.png"
    path = _make_placeholder(tech, dest, index=index)
    return tech, path, "placeholder"


def fetch_logos(
    tech_list: list[str],
    output_dir: str | Path,
) -> dict[str, str]:
    """
    Download logos for each technology in *tech_list* using parallel HTTP requests.

    Returns a mapping {tech_label: local_file_path}.
    """
    logo_dir = Path(output_dir) / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)

    # Determine which techs still need downloading (cache check)
    to_fetch: list[tuple[int, str, Path]] = []
    result: dict[str, str] = {}

    for index, tech in enumerate(tech_list):
        slug = slugify(tech)
        cached: Path | None = None
        for ext in (".png", ".jpg", ".jpeg", ".svg"):
            candidate = logo_dir / f"{slug}{ext}"
            if candidate.exists():
                cached = candidate
                break
        if cached:
            result[tech] = str(cached)
        else:
            to_fetch.append((index, tech, logo_dir))

    if not to_fetch:
        return result

    # Parallel fetch with a thread pool
    max_workers = min(8, len(to_fetch))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_logo_for_tech, args): args for args in to_fetch}
        for future in as_completed(futures):
            try:
                tech, path, source = future.result()
                print(f"  [IMG] {tech} → {source}")
                result[tech] = path
            except Exception as exc:
                _, tech_name, _ = futures[future]
                print(f"  [IMG] {tech_name} → error: {exc}")

    return result
