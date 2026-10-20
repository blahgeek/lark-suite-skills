#!/usr/bin/env python3
"""Mirror the official, digest-verified Lark Suite archive."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

INDEX_URL = (
    "https://open.feishu.cn/lark-cli/skills/isolated/"
    ".well-known/agent-skills/index.json"
)
ROOT = Path(__file__).resolve().parent.parent


def download(url, limit):
    if urlparse(url).scheme != "https":
        raise ValueError("Downloads must use HTTPS")
    with urlopen(url, timeout=60) as response:
        if urlparse(response.url).scheme != "https":
            raise ValueError("Download redirected away from HTTPS")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("Download exceeds size limit")
    return content


def extract_archive(content, digest, destination):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Missing or invalid SHA-256 digest")
    if hashlib.sha256(content).hexdigest() != digest.removeprefix("sha256:"):
        raise ValueError("Archive SHA-256 mismatch")

    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 128 * 1024 * 1024:
            raise ValueError("Archive exceeds extraction limits")
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] not in {"SKILL.md", "references"}
                or not (member.isfile() or member.isdir())
                or str(path) in seen
            ):
                raise ValueError(f"Unsafe archive member: {member.name}")
            seen.add(str(path))
            # Do not preserve upstream writable/executable mode bits.
            member.mode = 0o755 if member.isdir() else 0o644
        archive.extractall(destination, members=members, filter="data")

    if not (destination / "SKILL.md").is_file():
        raise ValueError("Archive has no root SKILL.md")
    if not any((destination / "references").glob("*/GUIDE.md")):
        raise ValueError("Archive has no child capability guides")


def sync(root=ROOT):
    index = json.loads(download(INDEX_URL, 1024 * 1024))
    skills = [skill for skill in index["skills"] if skill["name"] == "lark-suite"]
    if len(skills) != 1 or skills[0].get("type") != "archive":
        raise ValueError("Expected exactly one lark-suite archive in official index")
    skill = skills[0]
    url = urljoin(INDEX_URL, skill["url"])
    if urlparse(url).netloc != urlparse(INDEX_URL).netloc:
        raise ValueError("Archive URL must use the official index host")
    content = download(url, 32 * 1024 * 1024)

    # Validate the entire new tree before touching the previous mirror.
    with tempfile.TemporaryDirectory(prefix=".sync-", dir=root) as temporary:
        staged = Path(temporary) / "lark-suite"
        staged.mkdir()
        extract_archive(content, skill["digest"], staged)
        target = root / "lark-suite"
        backup = Path(temporary) / "previous"
        if target.exists():
            target.rename(backup)
        try:
            staged.rename(target)
        except BaseException:
            if backup.exists():
                backup.rename(target)
            raise

    print(f"Synced lark-suite ({skill['digest']})")


if __name__ == "__main__":
    sync()
