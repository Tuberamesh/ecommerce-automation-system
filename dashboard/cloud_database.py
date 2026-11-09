from pathlib import Path
import os

import requests
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "deployment_ecommerce.db"


def ensure_database() -> Path:
    # Use the original local database when developing locally.
    local_database = PROJECT_ROOT / "database" / "ecommerce.db"
    if local_database.is_file():
        return local_database

    # Streamlit Cloud: download the private release asset if needed.
    if DATABASE_PATH.is_file():
        return DATABASE_PATH

    try:
        token = st.secrets.get("GITHUB_TOKEN")
    except Exception:
        token = None

    if not token:
        # Allow local tests and CI to import the dashboard without cloud secrets.
        return DATABASE_PATH

    repo = st.secrets.get("GITHUB_REPO", "Tuberamesh/olist-dashboard-data")
    tag = st.secrets.get("GITHUB_RELEASE_TAG", "v1.0")
    asset_name = st.secrets.get(
        "GITHUB_ASSET_NAME", "deployment_ecommerce.db"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    release_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    response = requests.get(release_url, headers=headers, timeout=30)
    response.raise_for_status()

    release = response.json()
    asset = next(
        (item for item in release.get("assets", [])
         if item["name"] == asset_name),
        None,
    )

    if asset is None:
        raise FileNotFoundError(
            f"Release {tag} does not contain {asset_name}."
        )

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = DATABASE_PATH.with_suffix(".db.part")

    try:
        with requests.get(
            asset["url"],
            headers={**headers, "Accept": "application/octet-stream"},
            stream=True,
            timeout=(30, 120),
        ) as download:
            download.raise_for_status()

            with temporary_path.open("wb") as file:
                for chunk in download.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)

        if temporary_path.stat().st_size != asset["size"]:
            raise RuntimeError("Downloaded database size does not match GitHub asset.")

        os.replace(temporary_path, DATABASE_PATH)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return DATABASE_PATH
