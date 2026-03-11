"""
image_gatherer.py — Fetch logos and illustrations for detected technologies.

Strategy (in priority order):
  1. Clearbit Logo API  — https://logo.clearbit.com/{domain}
  2. Wikimedia Commons API — free tech SVG/PNG logos
  3. Simple coloured placeholder image (always succeeds)
"""

from __future__ import annotations

from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont  # type: ignore[import]

from techstack.utils import find_system_font, slugify

# ---------------------------------------------------------------------------
# Domain map: technology label → Clearbit domain
# ---------------------------------------------------------------------------
TECH_DOMAINS: dict[str, str] = {
    # Languages
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
    # Frameworks
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
    # Databases
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
    # Auth
    "OAuth": "oauth.net",
    "JWT": "jwt.io",
    "Auth0": "auth0.com",
    "Okta": "okta.com",
    "Keycloak": "keycloak.org",
    "NextAuth.js": "next-auth.js.org",
    "Supabase Auth": "supabase.com",
    # Messaging
    "Apache Kafka": "kafka.apache.org",
    "RabbitMQ": "rabbitmq.com",
    "Celery": "celeryq.dev",
    "NATS": "nats.io",
    # CI/CD
    "GitHub Actions": "github.com",
    "CircleCI": "circleci.com",
    "Jenkins": "jenkins.io",
    "GitLab CI": "gitlab.com",
    "Travis CI": "travis-ci.com",
    "Azure Pipelines": "azure.microsoft.com",
    # Containers / Infra
    "Docker": "docker.com",
    "Docker Compose": "docker.com",
    "Kubernetes": "kubernetes.io",
    "Helm": "helm.sh",
    "Terraform": "terraform.io",
    "Pulumi": "pulumi.com",
    "Serverless Framework": "serverless.com",
    "AWS CDK": "aws.amazon.com",
    "Ansible": "ansible.com",
    # Cloud
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

# Wikimedia Commons API fallbacks: tech label → search term
WIKIMEDIA_TERMS: dict[str, str] = {
    "JavaScript": "JavaScript_logo",
    "Node.js / npm": "Npm_logo",
    "Go": "Go_Logo_Blue",
    "Shell": "Bash_Logo_Colored",
    "Make": "GNU_Make_logo",
}

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "TechStackAnalyzer/1.0 (github.com)"})


def _clearbit_url(domain: str) -> str:
    return f"https://logo.clearbit.com/{domain}?size=256"


def _fetch_clearbit(tech: str, dest: Path) -> bool:
    domain = TECH_DOMAINS.get(tech)
    if not domain:
        return False
    try:
        resp = _SESSION.get(_clearbit_url(domain), timeout=10)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def _wikimedia_url(term: str) -> str | None:
    """Return a direct URL to the first image result on Wikimedia Commons."""
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": term,
        "srnamespace": "6",
        "srlimit": "1",
        "format": "json",
    }
    try:
        resp = _SESSION.get(api, params=params, timeout=10)
        data = resp.json()
        hits = data.get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        # Fetch the image URL
        info_resp = _SESSION.get(api, params={
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }, timeout=10)
        pages = info_resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            urls = page.get("imageinfo", [])
            if urls:
                return urls[0]["url"]
    except Exception:
        pass
    return None


def _fetch_wikimedia(tech: str, dest: Path) -> bool:
    term = WIKIMEDIA_TERMS.get(tech, tech + " logo")
    url = _wikimedia_url(term)
    if not url:
        return False
    try:
        resp = _SESSION.get(url, timeout=15)
        if resp.status_code == 200:
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


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
]


def _make_placeholder(tech: str, dest: Path, index: int = 0) -> None:
    """Create a simple coloured placeholder PNG when no logo is found."""
    bg_color, text_color = _PALETTE[index % len(_PALETTE)]
    img = Image.new("RGBA", (256, 256), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to fit text
    label = tech[:20] + ("…" if len(tech) > 20 else "")
    font_path = find_system_font(bold=True)
    try:
        font = ImageFont.truetype(font_path, size=24) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Center the text
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (256 - text_w) // 2
    y = (256 - text_h) // 2
    draw.text((x, y), label, fill=text_color, font=font)

    img.save(str(dest), "PNG")


def fetch_logos(
    tech_list: list[str],
    output_dir: str | Path,
) -> dict[str, str]:
    """
    Download logos for each technology in *tech_list*.

    Returns a mapping {tech_label: local_file_path}.
    """
    out = Path(output_dir) / "logos"
    out.mkdir(parents=True, exist_ok=True)

    result: dict[str, str] = {}
    for index, tech in enumerate(tech_list):
        slug = slugify(tech)
        # Check all candidate extensions
        cached: Path | None = None
        for ext in (".png", ".jpg", ".jpeg", ".svg"):
            candidate = out / f"{slug}{ext}"
            if candidate.exists():
                cached = candidate
                break

        if cached:
            result[tech] = str(cached)
            continue

        dest_png = out / f"{slug}.png"
        dest_jpg = out / f"{slug}.jpg"

        # Strategy 1 – Clearbit
        if _fetch_clearbit(tech, dest_png):
            print(f"  [IMG] {tech} → Clearbit logo")
            result[tech] = str(dest_png)
            continue

        # Strategy 2 – Wikimedia Commons
        if _fetch_wikimedia(tech, dest_jpg):
            print(f"  [IMG] {tech} → Wikimedia Commons")
            result[tech] = str(dest_jpg)
            continue

        # Strategy 3 – Placeholder
        print(f"  [IMG] {tech} → placeholder")
        _make_placeholder(tech, dest_png, index=index)
        result[tech] = str(dest_png)

    return result
