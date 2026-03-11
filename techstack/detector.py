"""
detector.py — GitHub API-based tech stack detection.

Scans a public GitHub repository (without cloning) and identifies:
  - Programming languages
  - Package manager / dependency files
  - Databases (ORM configs, connection strings, docker-compose services)
  - CI/CD pipelines
  - Containerisation & orchestration
  - Authentication / security libraries
  - Message brokers
  - Sharding / replication / IaC hints
  - Cloud-provider SDKs
"""

from __future__ import annotations

import re
from typing import Any

import requests
from github import Github
from github.Repository import Repository

# ---------------------------------------------------------------------------
# Helper pattern sets
# ---------------------------------------------------------------------------

LANG_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".swift": "Swift",
    ".scala": "Scala",
    ".r": "R",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".hs": "Haskell",
    ".lua": "Lua",
    ".jl": "Julia",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
}

PKG_MANAGER_FILES: dict[str, str] = {
    "package.json": "Node.js / npm",
    "package-lock.json": "Node.js / npm",
    "yarn.lock": "Node.js / Yarn",
    "pnpm-lock.yaml": "Node.js / pnpm",
    "requirements.txt": "Python / pip",
    "Pipfile": "Python / pipenv",
    "pyproject.toml": "Python / Poetry or PEP-517",
    "setup.py": "Python / setuptools",
    "setup.cfg": "Python / setuptools",
    "Cargo.toml": "Rust / Cargo",
    "go.mod": "Go Modules",
    "pom.xml": "Java / Maven",
    "build.gradle": "Java / Gradle",
    "build.gradle.kts": "Kotlin / Gradle",
    "Gemfile": "Ruby / Bundler",
    "composer.json": "PHP / Composer",
    "Package.swift": "Swift / SPM",
    "pubspec.yaml": "Dart / Flutter",
    "mix.exs": "Elixir / Mix",
    "stack.yaml": "Haskell / Stack",
    "cabal.project": "Haskell / Cabal",
    "deps.edn": "Clojure / deps",
    "project.clj": "Clojure / Leiningen",
    "CMakeLists.txt": "C/C++ / CMake",
    "Makefile": "Make",
    "meson.build": "C/C++ / Meson",
    "conanfile.txt": "C/C++ / Conan",
    "conanfile.py": "C/C++ / Conan",
    "vcpkg.json": "C/C++ / vcpkg",
    "Chart.yaml": "Helm Chart",
}

CICD_PATHS: dict[str, str] = {
    ".github/workflows": "GitHub Actions",
    ".circleci": "CircleCI",
    "Jenkinsfile": "Jenkins",
    ".gitlab-ci.yml": "GitLab CI",
    ".travis.yml": "Travis CI",
    "azure-pipelines.yml": "Azure Pipelines",
    ".drone.yml": "Drone CI",
    "bitbucket-pipelines.yml": "Bitbucket Pipelines",
    "Taskfile.yml": "Taskfile",
    "Taskfile.yaml": "Taskfile",
    ".buildkite": "Buildkite",
    "appveyor.yml": "AppVeyor",
}

CONTAINER_FILES: dict[str, str] = {
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "docker-compose.override.yml": "Docker Compose",
    "docker-compose.override.yaml": "Docker Compose",
    ".dockerignore": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "helm": "Helm",
    "skaffold.yaml": "Skaffold",
    "skaffold.yml": "Skaffold",
    "tilt.yml": "Tilt",
    "tiltfile": "Tilt",
}

IAC_FILES: dict[str, str] = {
    "main.tf": "Terraform",
    "variables.tf": "Terraform",
    "outputs.tf": "Terraform",
    "Pulumi.yaml": "Pulumi",
    "Pulumi.yml": "Pulumi",
    "serverless.yml": "Serverless Framework",
    "serverless.yaml": "Serverless Framework",
    "template.yaml": "AWS SAM / CloudFormation",
    "template.yml": "AWS SAM / CloudFormation",
    "cdk.json": "AWS CDK",
    "ansible.cfg": "Ansible",
    "playbook.yml": "Ansible",
    "playbook.yaml": "Ansible",
}

# Content patterns (regex) → (category, label)
CONTENT_PATTERNS: list[tuple[str, str, str]] = [
    # Databases
    (r"postgresql|postgres|pg_connect|psycopg|asyncpg", "database", "PostgreSQL"),
    (r"mysql|mysqlclient|pymysql|aiomysql", "database", "MySQL"),
    (r"mongodb|mongoose|pymongo|motor", "database", "MongoDB"),
    (r"redis(?!-om)", "database", "Redis"),
    (r"sqlite|aiosqlite", "database", "SQLite"),
    (r"elasticsearch|opensearch", "database", "Elasticsearch"),
    (r"cassandra|astra", "database", "Cassandra"),
    (r"dynamodb|DynamoDB", "database", "DynamoDB"),
    (r"firestore|firebase", "database", "Firebase / Firestore"),
    (r"neo4j|cypher", "database", "Neo4j"),
    (r"influxdb", "database", "InfluxDB"),
    (r"cockroachdb", "database", "CockroachDB"),
    (r"mariadb", "database", "MariaDB"),
    (r"supabase", "database", "Supabase"),
    (r"planetscale", "database", "PlanetScale"),
    # Auth / Security
    (r"oauth|oauth2|oauthlib", "auth", "OAuth"),
    (r"jwt|jsonwebtoken|pyjwt|jose", "auth", "JWT"),
    (r"passport", "auth", "Passport.js"),
    (r"auth0", "auth", "Auth0"),
    (r"okta", "auth", "Okta"),
    (r"keycloak", "auth", "Keycloak"),
    (r"firebase.?auth|firebaseauth", "auth", "Firebase Auth"),
    (r"nextauth", "auth", "NextAuth.js"),
    (r"supabase.?auth", "auth", "Supabase Auth"),
    (r"ldap|active.?directory", "auth", "LDAP / Active Directory"),
    (r"bcrypt|argon2|passlib", "auth", "Password Hashing"),
    (r"helmet", "auth", "Helmet (HTTP hardening)"),
    (r"cors", "auth", "CORS"),
    # Message brokers
    (r"kafka|confluent", "messaging", "Apache Kafka"),
    (r"rabbitmq|pika|amqp", "messaging", "RabbitMQ"),
    (r"redis.?pub.?sub|redispy|aioredis", "messaging", "Redis Pub/Sub"),
    (r"celery", "messaging", "Celery"),
    (r"sqs|sns(?!apshot)", "messaging", "AWS SQS/SNS"),
    (r"pubsub|google.cloud.pubsub", "messaging", "Google Pub/Sub"),
    (r"nats", "messaging", "NATS"),
    (r"zeromq|zmq", "messaging", "ZeroMQ"),
    (r"activemq", "messaging", "ActiveMQ"),
    (r"mqtt|paho", "messaging", "MQTT"),
    # Cloud providers
    (r"boto3|botocore|aws.?sdk|@aws-sdk|aws-cdk", "cloud", "AWS"),
    (r"google.cloud|gcloud|firebase.?admin|@google-cloud", "cloud", "Google Cloud"),
    (r"azure.?sdk|@azure|azure-identity", "cloud", "Azure"),
    (r"digitalocean|pydo", "cloud", "DigitalOcean"),
    (r"cloudflare|@cloudflare", "cloud", "Cloudflare"),
    (r"vercel|@vercel", "cloud", "Vercel"),
    (r"netlify", "cloud", "Netlify"),
    (r"heroku", "cloud", "Heroku"),
    (r"fly.io|flyctl", "cloud", "Fly.io"),
    # ORM / Data frameworks
    (r"sqlalchemy|alembic", "database", "SQLAlchemy / Alembic"),
    (r"prisma", "database", "Prisma ORM"),
    (r"typeorm|TypeORM", "database", "TypeORM"),
    (r"sequelize", "database", "Sequelize ORM"),
    (r"django.db|models\.Model", "database", "Django ORM"),
    (r"activerecord|ActiveRecord", "database", "ActiveRecord (Rails)"),
    (r"hibernate", "database", "Hibernate ORM"),
    (r"drizzle.?orm|drizzle-orm", "database", "Drizzle ORM"),
    (r"mikro.?orm|mikro-orm", "database", "MikroORM"),
    # Sharding / replication hints
    (r"replica(?:tion|_set)|sharding|shard_key|max_connections", "infra", "DB Sharding/Replication"),
    (r"pgbouncer|pgpool|patroni", "infra", "PG Pooling/HA"),
    (r"read_replica|readReplica|follower", "infra", "Read Replicas"),
    # Frameworks (for overview)
    (r"fastapi|FastAPI", "framework", "FastAPI"),
    (r"flask|Flask", "framework", "Flask"),
    (r"django|Django", "framework", "Django"),
    (r"express|Express", "framework", "Express.js"),
    (r"nestjs|NestJS|@nestjs", "framework", "NestJS"),
    (r"next\.?js|nextjs|\"next\"", "framework", "Next.js"),
    (r"nuxt|nuxtjs", "framework", "Nuxt.js"),
    (r"svelte(?:kit)?", "framework", "SvelteKit / Svelte"),
    (r"vue|vuejs|\"vue\"", "framework", "Vue.js"),
    (r"react|\"react\"", "framework", "React"),
    (r"angular|@angular", "framework", "Angular"),
    (r"spring.?boot|SpringBoot", "framework", "Spring Boot"),
    (r"rails|ruby.on.rails", "framework", "Ruby on Rails"),
    (r"laravel|Laravel", "framework", "Laravel"),
    (r"gin.?gonic|gin\.Default", "framework", "Gin (Go)"),
    (r"echo\.New|labstack.echo", "framework", "Echo (Go)"),
    (r"actix.?web|actix_web", "framework", "Actix-web (Rust)"),
    (r"axum|tokio", "framework", "Axum / Tokio (Rust)"),
    (r"phoenix|Phoenix", "framework", "Phoenix (Elixir)"),
]

# Docker Compose service → category
DOCKER_SERVICE_PATTERNS: list[tuple[str, str, str]] = [
    (r"postgres|postgresql", "database", "PostgreSQL"),
    (r"mysql|mariadb", "database", "MySQL / MariaDB"),
    (r"mongo(?:db)?", "database", "MongoDB"),
    (r"redis", "database", "Redis"),
    (r"rabbitmq", "messaging", "RabbitMQ"),
    (r"kafka|zookeeper", "messaging", "Apache Kafka"),
    (r"elasticsearch|opensearch", "database", "Elasticsearch"),
    (r"kibana", "infra", "Kibana"),
    (r"grafana", "infra", "Grafana"),
    (r"prometheus", "infra", "Prometheus"),
    (r"nginx|traefik|caddy", "infra", "Reverse Proxy"),
    (r"influxdb", "database", "InfluxDB"),
    (r"cassandra", "database", "Cassandra"),
    (r"nats", "messaging", "NATS"),
]


def _get_tree(repo: Repository) -> list[dict[str, Any]]:
    """Return the full recursive file tree of the default branch."""
    try:
        branch = repo.default_branch
        tree = repo.get_git_tree(branch, recursive=True)
        return [{"path": e.path, "type": e.type} for e in tree.tree]
    except Exception:
        return []


def _fetch_file_content(repo: Repository, path: str) -> str:
    """Fetch raw text content of a single file (best-effort, ≤1 MB)."""
    try:
        content_file = repo.get_contents(path)
        if isinstance(content_file, list):
            return ""
        raw = content_file.decoded_content
        return raw.decode("utf-8", errors="ignore") if raw else ""
    except Exception:
        return ""


def _scan_content_patterns(text: str) -> dict[str, set[str]]:
    """Return category → set of labels matched in *text*."""
    found: dict[str, set[str]] = {}
    lower = text.lower()
    for pattern, category, label in CONTENT_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            found.setdefault(category, set()).add(label)
    return found


def _scan_docker_compose(text: str) -> dict[str, set[str]]:
    """Extract service names from docker-compose and map to categories."""
    found: dict[str, set[str]] = {}
    service_block_re = re.compile(
        r"^\s{2,4}(\w[\w-]*):\s*$", re.MULTILINE
    )
    for match in service_block_re.finditer(text):
        svc = match.group(1)
        for pattern, category, label in DOCKER_SERVICE_PATTERNS:
            if re.search(pattern, svc, re.IGNORECASE):
                found.setdefault(category, set()).add(label)
    # Also scan image: lines
    image_re = re.compile(r"image:\s*([^\s#]+)", re.IGNORECASE)
    for img_match in image_re.finditer(text):
        img = img_match.group(1)
        for pattern, category, label in DOCKER_SERVICE_PATTERNS:
            if re.search(pattern, img, re.IGNORECASE):
                found.setdefault(category, set()).add(label)
    return found


# ---------------------------------------------------------------------------
# Files whose content we want to fully fetch for deep scanning
# ---------------------------------------------------------------------------
DEEP_SCAN_NAMES: set[str] = {
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "docker-compose.yml",
    "docker-compose.yaml",
    "docker-compose.override.yml",
    "docker-compose.override.yaml",
    ".env",
    ".env.example",
    ".env.sample",
    "Dockerfile",
}


def detect(repo_url: str, github_token: str | None = None) -> dict[str, Any]:
    """
    Main entry point.  Accepts a GitHub repo URL, returns a structured
    dict describing the detected tech stack.
    """
    # Parse owner/repo from URL
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url.strip()
    )
    if not match:
        raise ValueError(f"Not a valid GitHub repo URL: {repo_url!r}")
    owner, repo_name = match.group(1), match.group(2)

    g = Github(github_token) if github_token else Github()
    repo: Repository = g.get_repo(f"{owner}/{repo_name}")

    # Seed result
    result: dict[str, Any] = {
        "repo_url": repo_url,
        "repo_name": repo.full_name,
        "description": repo.description or "",
        "default_branch": repo.default_branch,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "languages": {},
        "package_managers": [],
        "frameworks": [],
        "databases": [],
        "auth": [],
        "messaging": [],
        "cicd": [],
        "containers": [],
        "iac": [],
        "cloud": [],
        "infra": [],
    }

    # --- GitHub Linguist language breakdown ---
    try:
        lang_bytes = repo.get_languages()
        result["languages"] = dict(lang_bytes)
    except Exception:
        pass

    # Also detect languages via file extensions (supplement Linguist)
    tree = _get_tree(repo)
    all_paths = [e["path"] for e in tree if e["type"] == "blob"]

    ext_langs: dict[str, int] = {}
    for path in all_paths:
        ext = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        lang = LANG_EXTENSIONS.get(ext)
        if lang:
            ext_langs[lang] = ext_langs.get(lang, 0) + 1

    for lang, count in ext_langs.items():
        if lang not in result["languages"]:
            result["languages"][lang] = count

    # --- Package manager files ---
    path_set = set(all_paths)
    for fname, label in PKG_MANAGER_FILES.items():
        # exact match OR in any subdirectory (first occurrence only)
        if fname in path_set or any(p.endswith("/" + fname) for p in path_set):
            if label not in result["package_managers"]:
                result["package_managers"].append(label)

    # --- CI/CD ---
    for ci_path, label in CICD_PATHS.items():
        if any(p == ci_path or p.startswith(ci_path + "/") or p.startswith(ci_path) for p in path_set):
            if label not in result["cicd"]:
                result["cicd"].append(label)

    # --- Containerisation ---
    for cpath, label in CONTAINER_FILES.items():
        if any(
            p == cpath
            or p.startswith(cpath + "/")
            or p.lower() == cpath.lower()
            for p in path_set
        ):
            if label not in result["containers"]:
                result["containers"].append(label)

    # --- IaC ---
    for ipath, label in IAC_FILES.items():
        if any(p == ipath or p.endswith("/" + ipath) for p in path_set):
            if label not in result["iac"]:
                result["iac"].append(label)

    # --- Deep-scan selected files for content patterns ---
    aggregate: dict[str, set[str]] = {}

    files_to_scan: list[str] = []
    for path in all_paths:
        fname = path.rsplit("/", 1)[-1]
        if fname in DEEP_SCAN_NAMES:
            files_to_scan.append(path)

    # Also scan up to 30 source files (varied extensions) for dependency hints
    source_exts = {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".php", ".cs"}
    source_files = [p for p in all_paths if ("." + p.rsplit(".", 1)[-1]) in source_exts]
    # Prioritise root-level files and common config names
    source_files.sort(key=lambda p: (p.count("/"), p))
    files_to_scan.extend(source_files[:30])

    seen: set[str] = set()
    for path in files_to_scan:
        if path in seen:
            continue
        seen.add(path)
        content = _fetch_file_content(repo, path)
        if not content:
            continue
        matches = _scan_content_patterns(content)
        for cat, labels in matches.items():
            aggregate.setdefault(cat, set()).update(labels)

        # Extra: docker-compose deep scan
        fname = path.rsplit("/", 1)[-1]
        if "docker-compose" in fname.lower():
            dc_matches = _scan_docker_compose(content)
            for cat, labels in dc_matches.items():
                aggregate.setdefault(cat, set()).update(labels)

    # Merge aggregate into result lists
    cat_to_key = {
        "database": "databases",
        "auth": "auth",
        "messaging": "messaging",
        "cloud": "cloud",
        "infra": "infra",
        "framework": "frameworks",
    }
    for cat, key in cat_to_key.items():
        for label in sorted(aggregate.get(cat, [])):
            if label not in result[key]:
                result[key].append(label)

    return result
