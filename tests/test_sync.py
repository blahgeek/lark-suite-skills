import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "sync", Path(__file__).resolve().parents[1] / "scripts" / "sync.py"
)
mirror = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)


def archive_bytes(extra=None):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name in ["SKILL.md", "references/lark-doc/GUIDE.md"]:
            data = b"test guide"
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        if extra:
            archive.addfile(extra)
    return buffer.getvalue()


def index_bytes(content):
    return json.dumps({"skills": [{
        "name": "lark-suite",
        "type": "archive",
        "url": "./lark-suite.tar.gz",
        "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
    }]}).encode()


class SyncTests(unittest.TestCase):
    def test_replaces_tree_and_removes_stale_files(self):
        content = archive_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lark-suite").mkdir()
            (root / "lark-suite" / "stale.md").write_text("obsolete")
            with patch.object(mirror, "download", side_effect=[index_bytes(content), content]) as fetch:
                mirror.sync(root)
            self.assertTrue((root / "lark-suite" / "SKILL.md").is_file())
            self.assertFalse((root / "lark-suite" / "stale.md").exists())
            self.assertEqual(fetch.call_args_list[1].args[0],
                             mirror.INDEX_URL.rsplit("/", 1)[0] + "/lark-suite.tar.gz")

    def test_digest_failure_preserves_existing_tree(self):
        content = archive_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lark-suite").mkdir()
            existing = root / "lark-suite" / "SKILL.md"
            existing.write_text("previous")
            with patch.object(mirror, "download",
                              side_effect=[index_bytes(content), content + b"corrupted"]):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    mirror.sync(root)
            self.assertEqual(existing.read_text(), "previous")

    def test_rejects_traversal_and_links(self):
        traversal = tarfile.TarInfo("references/../../outside")
        link = tarfile.TarInfo("references/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        for member in [traversal, link]:
            with self.subTest(name=member.name), tempfile.TemporaryDirectory() as temporary:
                content = archive_bytes(member)
                digest = "sha256:" + hashlib.sha256(content).hexdigest()
                with self.assertRaisesRegex(ValueError, "Unsafe archive"):
                    mirror.extract_archive(content, digest, Path(temporary))

    def test_rejects_incomplete_archive(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz"):
            pass
        content = buffer.getvalue()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "no root SKILL.md"):
                mirror.extract_archive(content, "sha256:" + hashlib.sha256(content).hexdigest(),
                                       Path(temporary))


if __name__ == "__main__":
    unittest.main()
