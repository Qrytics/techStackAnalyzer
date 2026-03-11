"""
script_generator.py — Generate a structured narration script from detected stack data.

Each section is 2–4 sentences designed to read naturally when spoken aloud.
Returns a list of dicts: [{"title": str, "text": str, "techs": list[str]}]

Optional Ollama Enhancement
---------------------------
If ``use_ollama=True`` is passed to ``generate()``, this module will call a
locally-running Ollama instance (http://localhost:11434) to rewrite each
section into richer, more engaging prose.  Ollama is free and open-source —
see https://ollama.com.  If Ollama is unavailable, the built-in template
text is used automatically as a fallback.
"""

from __future__ import annotations

import json
from typing import Any


_ORM_LABELS: frozenset[str] = frozenset({
    "SQLAlchemy / Alembic",
    "Prisma ORM",
    "TypeORM",
    "Sequelize ORM",
    "Django ORM",
    "ActiveRecord (Rails)",
    "Hibernate ORM",
    "Drizzle ORM",
    "MikroORM",
})


def _pluralise(items: list[str]) -> str:
    """Join a list of items into a human-readable, comma-separated string."""
    if not items:
        return "none detected"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _format_stars(n: int) -> str:
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return f"{n:,}"


# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------
def _enhance_with_ollama(
    sections: list[dict[str, Any]],
    stack: dict[str, Any],
    model: str = "llama3",
) -> list[dict[str, Any]]:
    """
    Use a locally-running Ollama model to rewrite each section's narration
    text into richer, more engaging prose.

    If Ollama is not available (not installed, not running, or any error),
    the original template text is returned unchanged.

    Parameters
    ----------
    sections : list returned by the template generator
    stack    : raw stack detection result (for extra context)
    model    : Ollama model name (default: ``llama3``)
    """
    try:
        import requests as _req
    except ImportError:
        return sections

    system_prompt = (
        "You are a professional tech narrator writing scripts for short, engaging YouTube "
        "explainer videos about software repositories. "
        "Rewrite the following narration section to be more vivid, conversational, and "
        "enthusiastic — like a knowledgeable friend explaining a cool open-source project. "
        "Keep it concise (3–5 sentences max), accurate to the facts provided, and suitable "
        "for text-to-speech. Return only the rewritten narration text with no extra commentary."
    )

    enhanced: list[dict[str, Any]] = []
    _ollama_available = True  # flip False on first connection error to suppress repeat noise

    for section in sections:
        original_text = section["text"]
        user_prompt = (
            f"Section title: \"{section['title']}\"\n\n"
            f"Original narration:\n{original_text}\n\n"
            f"Repository: {stack.get('repo_name', 'unknown')}\n"
            f"Stars: {stack.get('stars', 0):,} | Forks: {stack.get('forks', 0):,}\n"
        )
        if _ollama_available:
            try:
                resp = _req.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model,
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 256},
                    },
                    timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    new_text = data.get("response", "").strip()
                    if new_text:
                        enhanced.append({**section, "text": new_text})
                        print(f"  [Ollama] ✓ {section['title']!r}")
                        continue
            except (ConnectionRefusedError, Exception) as exc:
                # Detect connection failures to suppress repeated noise
                exc_str = str(exc)
                if "Connection refused" in exc_str or "Max retries exceeded" in exc_str or "NewConnectionError" in exc_str:
                    print("  [Ollama] Not reachable at localhost:11434 — falling back to template text.")
                    _ollama_available = False
                else:
                    _short = exc_str.split("\n")[0][:120]
                    print(f"  [Ollama] {section['title']!r} → {_short}")
        enhanced.append(section)

    return enhanced


# ---------------------------------------------------------------------------
# Template-based script generation
# ---------------------------------------------------------------------------
def generate(
    stack: dict[str, Any],
    use_ollama: bool = False,
    ollama_model: str = "llama3",
) -> list[dict[str, Any]]:
    """
    Generate a narration script from a stack detection result.

    Parameters
    ----------
    stack        : dict returned by ``detector.detect()``
    use_ollama   : if True, attempt to enhance sections via a local Ollama model
    ollama_model : Ollama model name (default: ``llama3``)

    Returns
    -------
    List of section dicts: [{"title": str, "text": str, "techs": list[str]}, …]
    """
    repo_name   = stack.get("repo_name", "this repository")
    description = stack.get("description", "")
    stars       = stack.get("stars", 0)
    forks       = stack.get("forks", 0)

    languages        = sorted(stack.get("languages", {}).keys())
    package_managers = stack.get("package_managers", [])
    frameworks       = stack.get("frameworks", [])
    databases        = stack.get("databases", [])
    auth             = stack.get("auth", [])
    messaging        = stack.get("messaging", [])
    cicd             = stack.get("cicd", [])
    containers       = stack.get("containers", [])
    iac              = stack.get("iac", [])
    cloud            = stack.get("cloud", [])
    infra            = stack.get("infra", [])

    sections: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Section 1 – Overview
    # ------------------------------------------------------------------
    star_str = _format_stars(stars)
    overview_text = f"Let's take a deep dive into the tech stack powering {repo_name}. "
    if description:
        overview_text += f"{description.rstrip('.')} — which already tells us a lot about its ambitions. "
    overview_text += (
        f"With {star_str} GitHub stars and {forks:,} forks, this project has earned real "
        "traction in the developer community. "
    )
    if languages:
        primary = languages[0]
        others = languages[1:4]
        overview_text += (
            f"It's written primarily in {primary}"
            + (f", with contributions also spanning {_pluralise(others)}" if others else "")
            + ", setting a strong foundation for what's ahead. "
        )
    sections.append({"title": "Overview", "text": overview_text.strip(), "techs": []})

    # ------------------------------------------------------------------
    # Section 2 – Languages & Frameworks
    # ------------------------------------------------------------------
    lang_text = ""
    if languages:
        lang_text += f"At its core, this project is built in {_pluralise(languages[:5])}. "
    if frameworks:
        if len(frameworks) == 1:
            lang_text += f"{frameworks[0]} is the primary application framework driving the product. "
        else:
            lang_text += (
                f"The engineering team has chosen {_pluralise(frameworks)} as their "
                "application framework stack — a combination that balances developer "
                "productivity with runtime performance. "
            )
    if package_managers:
        lang_text += f"Dependencies are wrangled with {_pluralise(package_managers)}. "
    if not lang_text:
        lang_text = (
            "No dominant language or framework was detected — this may be a polyglot "
            "codebase or one that relies heavily on configuration and scripts. "
        )
    sections.append({
        "title": "Languages & Frameworks",
        "text": lang_text.strip(),
        "techs": languages[:5] + frameworks,
    })

    # ------------------------------------------------------------------
    # Section 3 – Data Layer
    # ------------------------------------------------------------------
    data_text = ""
    if databases:
        data_text += f"Data persistence is handled by {_pluralise(databases)}. "
        orm_present = [d for d in databases if d in _ORM_LABELS]
        if orm_present:
            data_text += (
                f"An ORM layer — {_pluralise(orm_present)} — abstracts raw SQL, making the "
                "data access code safer and more maintainable. "
            )
        if infra:
            data_text += (
                f"Infrastructure tooling like {_pluralise(infra)} points to thoughtful "
                "attention to scalability and high availability. "
            )
    else:
        data_text = (
            "No explicit database configuration was found in the scanned files. "
            "The project may rely on an embedded store, a managed cloud database, or "
            "an external service not referenced directly in the repo. "
        )
    sections.append({
        "title": "Data Layer",
        "text": data_text.strip(),
        "techs": databases + infra,
    })

    # ------------------------------------------------------------------
    # Section 4 – Infrastructure & Cloud
    # ------------------------------------------------------------------
    infra_text = ""
    all_infra: list[str] = []
    if containers:
        all_infra.extend(containers)
        infra_text += (
            f"Containerisation is handled with {_pluralise(containers)}, "
            "ensuring consistent environments from development to production. "
        )
    if iac:
        all_infra.extend(iac)
        infra_text += (
            f"Infrastructure-as-code via {_pluralise(iac)} makes the whole environment "
            "reproducible and version-controlled. "
        )
    if cloud:
        all_infra.extend(cloud)
        infra_text += (
            f"Cloud integrations were detected for {_pluralise(cloud)}, "
            "indicating a cloud-native or hybrid deployment strategy. "
        )
    if not infra_text:
        infra_text = (
            "No containerisation, IaC tools, or cloud-provider SDKs were found. "
            "The project might be deployed on a traditional host or a "
            "platform-as-a-service that handles infrastructure transparently. "
        )
    sections.append({
        "title": "Infrastructure & Cloud",
        "text": infra_text.strip(),
        "techs": all_infra,
    })

    # ------------------------------------------------------------------
    # Section 5 – Security & Authentication
    # ------------------------------------------------------------------
    sec_text = ""
    if auth:
        sec_text += (
            f"Security and authentication are powered by {_pluralise(auth)}. "
        )
        if any("JWT" in a for a in auth):
            sec_text += (
                "JSON Web Tokens provide stateless session management — a hallmark of "
                "modern API-first and microservice architectures. "
            )
        if any("OAuth" in a for a in auth):
            sec_text += (
                "OAuth integration lets users sign in via trusted third-party providers, "
                "reducing friction and keeping credentials off the server. "
            )
        if any("bcrypt" in a.lower() or "argon" in a.lower() or "passlib" in a.lower() for a in auth):
            sec_text += (
                "Strong password hashing with a battle-tested algorithm signals "
                "a security-conscious team. "
            )
    else:
        sec_text = (
            "No dedicated auth libraries were detected. Access control may be "
            "delegated to the framework, an API gateway, or an external identity provider. "
        )
    sections.append({
        "title": "Security & Authentication",
        "text": sec_text.strip(),
        "techs": auth,
    })

    # ------------------------------------------------------------------
    # Section 6 – Messaging & Async
    # ------------------------------------------------------------------
    msg_text = ""
    if messaging:
        msg_text += f"Async workloads are managed through {_pluralise(messaging)}. "
        if any("Kafka" in m for m in messaging):
            msg_text += (
                "Apache Kafka's high-throughput event streaming backbone enables "
                "fully decoupled, resilient microservice communication at scale. "
            )
        if any("Celery" in m for m in messaging):
            msg_text += (
                "Celery offloads long-running tasks to background workers, "
                "keeping the main request path snappy. "
            )
        if any("RabbitMQ" in m for m in messaging):
            msg_text += (
                "RabbitMQ's flexible routing model makes it a solid choice for "
                "reliable task queues and pub/sub patterns. "
            )
    else:
        msg_text = (
            "No dedicated message broker or async task queue was detected. "
            "The project likely relies on synchronous request-response patterns, "
            "which is perfectly appropriate for many use cases. "
        )
    sections.append({
        "title": "Messaging & Async",
        "text": msg_text.strip(),
        "techs": messaging,
    })

    # ------------------------------------------------------------------
    # Section 7 – CI/CD Pipelines
    # ------------------------------------------------------------------
    cicd_text = ""
    if cicd:
        cicd_text += f"Continuous integration and delivery run on {_pluralise(cicd)}. "
        if "GitHub Actions" in cicd:
            cicd_text += (
                "GitHub Actions keeps CI tightly coupled to the repository, "
                "running tests and deployments automatically on every push. "
            )
        if "GitLab CI" in cicd:
            cicd_text += (
                "GitLab CI provides a rich, built-in pipeline experience with "
                "container-native jobs and tight merge-request integration. "
            )
        cicd_text += (
            "Automated pipelines mean faster feedback loops, fewer integration "
            "surprises, and a higher-quality release process overall. "
        )
    else:
        cicd_text = (
            "No CI/CD pipeline configuration was found in this repository. "
            "The project may use an external CI service or manual deployment workflows. "
        )
    sections.append({
        "title": "CI/CD Pipelines",
        "text": cicd_text.strip(),
        "techs": cicd,
    })

    # ------------------------------------------------------------------
    # Section 8 – Summary
    # ------------------------------------------------------------------
    all_key_techs: list[str] = list(dict.fromkeys(
        languages[:3] + frameworks[:3] + databases[:3] + containers[:2] + cicd[:2] + cloud[:2]
    ))

    summary_text = (
        f"To wrap up — {repo_name} is a "
        + (f"{languages[0]}-based " if languages else "")
        + "project with a thoughtfully assembled technology stack. "
    )
    if all_key_techs:
        summary_text += (
            f"The headline technologies are {_pluralise(all_key_techs[:6])}, "
            "working together to deliver a robust, maintainable codebase. "
        )
    summary_text += (
        "This deep-dive was generated automatically by the Tech Stack Analyzer. "
        "Check the full JSON report for the complete picture."
    )
    sections.append({
        "title": "Summary",
        "text": summary_text.strip(),
        "techs": all_key_techs[:6],
    })

    # ------------------------------------------------------------------
    # Optional Ollama enhancement
    # ------------------------------------------------------------------
    if use_ollama:
        print(f"\n  [Ollama] Enhancing scripts with model: {ollama_model!r} …")
        sections = _enhance_with_ollama(sections, stack, model=ollama_model)

    return sections
