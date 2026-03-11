"""
script_generator.py — Generate a structured narration script from detected stack data.

Each section is 2–4 sentences designed to read naturally when spoken aloud.
Returns a list of dicts: [{"title": str, "text": str, "techs": list[str]}]
"""

from __future__ import annotations

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


def generate(stack: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Generate a narration script from a stack detection result.

    Returns a list of section dicts:
        [{"title": str, "text": str, "techs": list[str]}, ...]
    """
    repo_name = stack.get("repo_name", "this repository")
    description = stack.get("description", "")
    stars = stack.get("stars", 0)
    forks = stack.get("forks", 0)

    languages = sorted(stack.get("languages", {}).keys())
    package_managers = stack.get("package_managers", [])
    frameworks = stack.get("frameworks", [])
    databases = stack.get("databases", [])
    auth = stack.get("auth", [])
    messaging = stack.get("messaging", [])
    cicd = stack.get("cicd", [])
    containers = stack.get("containers", [])
    iac = stack.get("iac", [])
    cloud = stack.get("cloud", [])
    infra = stack.get("infra", [])

    sections: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Section 1 – Overview
    # ------------------------------------------------------------------
    overview_text = (
        f"Welcome to the tech stack deep-dive for {repo_name}. "
    )
    if description:
        overview_text += f"According to its description, this project {description.rstrip('.')}. "
    overview_text += (
        f"The repository has earned {stars:,} stars and been forked {forks:,} times on GitHub, "
        "indicating a healthy level of community interest. "
    )
    if languages:
        primary = languages[0]
        others = languages[1:4]
        overview_text += (
            f"The primary programming language is {primary}"
            + (f", with additional code written in {_pluralise(others)}" if others else "")
            + ". "
        )
    sections.append({
        "title": "Overview",
        "text": overview_text.strip(),
        "techs": [],
    })

    # ------------------------------------------------------------------
    # Section 2 – Languages & Frameworks
    # ------------------------------------------------------------------
    lang_text = ""
    if languages:
        lang_text += (
            f"This project is built primarily in {_pluralise(languages[:5])}. "
        )
    if frameworks:
        lang_text += (
            f"The following application frameworks were detected: {_pluralise(frameworks)}. "
        )
    if package_managers:
        lang_text += (
            f"Dependencies are managed with {_pluralise(package_managers)}. "
        )
    if not lang_text:
        lang_text = "No specific languages or frameworks were clearly detected in this repository. "

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
        data_text += (
            f"The data layer relies on {_pluralise(databases)}. "
        )
        if any(d in _ORM_LABELS for d in databases):
            data_text += (
                "An ORM layer is present, abstracting direct SQL queries and providing "
                "schema management capabilities. "
            )
        if infra:
            data_text += (
                f"Infrastructure tooling such as {_pluralise(infra)} suggests attention "
                "to high availability and scalability. "
            )
    else:
        data_text = (
            "No explicit database configurations were detected in the scanned files. "
            "The project may use an embedded store or external managed service not "
            "referenced directly in the repository. "
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
    all_infra_items: list[str] = []

    if containers:
        all_infra_items.extend(containers)
        infra_text += f"Containerisation is handled via {_pluralise(containers)}. "
    if iac:
        all_infra_items.extend(iac)
        infra_text += (
            f"Infrastructure-as-code tooling includes {_pluralise(iac)}, enabling "
            "reproducible environment provisioning. "
        )
    if cloud:
        all_infra_items.extend(cloud)
        infra_text += (
            f"Cloud provider integrations were detected for {_pluralise(cloud)}. "
        )
    if not infra_text:
        infra_text = (
            "No containerisation, infrastructure-as-code, or cloud-provider SDKs "
            "were identified in the scanned files. The project may be deployed on "
            "a traditional host or platform-as-a-service. "
        )

    sections.append({
        "title": "Infrastructure & Cloud",
        "text": infra_text.strip(),
        "techs": all_infra_items,
    })

    # ------------------------------------------------------------------
    # Section 5 – Security & Authentication
    # ------------------------------------------------------------------
    sec_text = ""
    if auth:
        sec_text += (
            f"Authentication and security are implemented using {_pluralise(auth)}. "
        )
        if any("JWT" in a for a in auth):
            sec_text += (
                "JSON Web Tokens are used for stateless session management, "
                "which is a common pattern in API-first architectures. "
            )
        if any("OAuth" in a for a in auth):
            sec_text += (
                "OAuth integration allows users to authenticate via third-party providers. "
            )
    else:
        sec_text = (
            "No explicit authentication or security libraries were detected. "
            "Authorization logic may be handled by a framework built-in or an external service. "
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
        msg_text += (
            f"Asynchronous messaging is facilitated through {_pluralise(messaging)}. "
        )
        if any("Kafka" in m for m in messaging):
            msg_text += (
                "Apache Kafka provides a high-throughput, distributed event streaming backbone "
                "that enables decoupled microservice communication. "
            )
        if any("Celery" in m for m in messaging):
            msg_text += (
                "Celery is used for background task processing, likely backed by Redis or RabbitMQ "
                "as the task broker. "
            )
    else:
        msg_text = (
            "No dedicated message broker or async task queue was detected. "
            "The project may rely on synchronous request-response patterns. "
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
        cicd_text += (
            f"Continuous integration and delivery are powered by {_pluralise(cicd)}. "
        )
        if "GitHub Actions" in cicd:
            cicd_text += (
                "GitHub Actions workflows automate testing, building, and deployment "
                "directly within the repository. "
            )
        cicd_text += (
            "Automated pipelines reduce manual effort and catch regressions early "
            "in the development cycle. "
        )
    else:
        cicd_text = (
            "No CI/CD pipeline configuration files were found in this repository. "
            "The project may use an external CI system or deployments may be manual. "
        )

    sections.append({
        "title": "CI/CD Pipelines",
        "text": cicd_text.strip(),
        "techs": cicd,
    })

    # ------------------------------------------------------------------
    # Section 8 – Summary
    # ------------------------------------------------------------------
    all_techs: list[str] = (
        languages[:3]
        + frameworks[:3]
        + databases[:3]
        + containers[:2]
        + cicd[:2]
        + cloud[:2]
    )
    unique_techs = list(dict.fromkeys(all_techs))

    summary_text = (
        f"To summarise, {repo_name} is a "
        + (f"{languages[0]}-based " if languages else "")
        + "project with a well-defined technology footprint. "
    )
    if unique_techs:
        summary_text += (
            f"Key technologies include {_pluralise(unique_techs[:6])}. "
        )
    summary_text += (
        "This analysis was generated automatically by the Tech Stack Analyzer tool. "
        "For the full machine-readable breakdown, see the accompanying stack report JSON file."
    )

    sections.append({
        "title": "Summary",
        "text": summary_text.strip(),
        "techs": unique_techs[:6],
    })

    return sections
