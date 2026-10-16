"""Publish verified prebuilt assets using this repository's GITHUB_TOKEN."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from artifact import checksum, validate_tag


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True).strip()


def latest_stable(repo):
    pages = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"))
    releases = [release for page in pages for release in page if not release["draft"] and not release["prerelease"]]
    candidates = []
    for release in releases:
        try:
            version, prerelease = validate_tag(release["tag_name"])
        except ValueError:
            continue
        if not prerelease:
            candidates.append((version, release["tag_name"]))
    return max(candidates)[1] if candidates else ""


def publish(repo, tag, directory):
    _, prerelease = validate_tag(tag)
    directory = Path(directory)
    # Listing distinguishes an absent release from an API failure; never treat a 403/500 as absent.
    releases = json.loads(gh("api", "--paginate", "--slurp", f"repos/{repo}/releases?per_page=100"))
    existing = next((r for page in releases for r in page if r["tag_name"] == tag), None)
    if existing and existing["author"]["login"] != "github-actions[bot]":
        raise ValueError("Release author must be github-actions[bot]")
    if not existing:
        args = ["release", "create", tag, "--repo", repo, "--verify-tag", "--draft", "--title", tag,
                "--notes", "Prebuilt XBond Dashboard. Verify dashboard.zip with SHA256SUMS."]
        if prerelease:
            args.append("--prerelease")
        gh(*args)
        existing = json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))
    # Validate every existing asset before making any upload or publication mutation.
    assets = {asset["name"]: asset for asset in existing["assets"]}
    for name in ("dashboard.zip", "SHA256SUMS"):
        if name in assets:
            content = subprocess.check_output(["gh", "api", "-H", "Accept: application/octet-stream",
                                              f"repos/{repo}/releases/assets/{assets[name]['id']}"])
            if hashlib.sha256(content).hexdigest() != checksum(directory / name):
                raise ValueError(f"Refusing to replace different Release bytes: {name}")
    for name in ("dashboard.zip", "SHA256SUMS"):
        if name not in assets:
            gh("release", "upload", tag, str(directory / name), "--repo", repo)
    gh("release", "edit", tag, "--repo", repo, "--draft=false", "--latest=false")
    if not prerelease and latest_stable(repo) == tag:
        gh("release", "edit", tag, "--repo", repo, "--latest=true")
    release = json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))
    if release["author"]["login"] != "github-actions[bot]":
        raise ValueError("Unexpected Release author")
    print(f"Published {tag} by {release['author']['login']}")


if __name__ == "__main__":
    repo = os.environ["GITHUB_REPOSITORY"]
    if sys.argv[1] == "latest":
        print(latest_stable(repo))
    else:
        publish(repo, sys.argv[1], sys.argv[2])
