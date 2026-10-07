#!/usr/bin/env python3
"""Exercise retirement through its CLI using disposable project directories."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts/retire.py"
sys.path.insert(0, str(ROOT / "scripts"))
from kanon_format import find, parse
import retire

PARTIAL = """---
task: Two outcomes
opened: 2026-09-02
closed: null
slots: 2
source: issue #1
---

## Gathered
- Constraint · issue #1

## Acceptance
- [x] 1. First result · check: test · proof: out/report.txt
- [ ] 2. Remaining result · check: test

## Failures
[!] 2 · tried: test · returned: missing output · 2026-09-02
"""


class RetirementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.folder = self.root / "_kanon"
        self.folder.mkdir()
        self.source = self.folder / "task.md"
        self.source.write_text(PARTIAL, encoding="utf-8")

    def run_cli(self, *args, ok=True):
        env = dict(os.environ)
        env.pop("KANON_DIR", None)
        result = subprocess.run([sys.executable, str(CLI), *map(str, args)],
                                cwd=self.root, env=env, capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def archive(self, disposition="cancelled", *extra):
        self.run_cli("archive", self.source, "--disposition", disposition,
                     "--reason", "Changed priorities", "--decision-source",
                     "owner instruction #1", *extra, "--apply")
        return next(p for p in (self.folder / "archive").glob("*.md")
                    if p.name != "LOG.md")

    def test_preview_is_read_only(self):
        self.run_cli("archive", self.source, "--disposition", "cancelled",
                     "--reason", "Changed priorities", "--decision-source", "owner #1")
        self.assertEqual(self.source.read_text(), PARTIAL)
        self.assertFalse((self.folder / "archive").exists())

    def test_partial_archive_preserves_proof_and_failure(self):
        archived = self.archive()
        self.assertFalse(self.source.exists())
        self.assertTrue(archived.read_text().startswith(PARTIAL))
        doc = parse(archived)
        self.assertEqual([i.number for i in doc.open_items], [2])
        self.assertEqual(doc.closed_on, "")
        self.assertEqual(doc.failures[0][1]["returned"], "missing output")
        self.assertEqual(find(self.root)[0], [])

    def test_deferred_requires_continuation_and_revisit(self):
        self.run_cli("archive", self.source, "--disposition", "deferred",
                     "--reason", "Later", "--decision-source", "owner #1", ok=False)
        self.assertTrue(self.source.exists())
        archived = self.archive("deferred", "--continued-in", "backlog #2",
                                "--revisit", "After launch")
        self.assertIn("backlog #2", archived.read_text())

    def test_completed_cannot_hide_open_item(self):
        self.run_cli("archive", self.source, "--disposition", "completed",
                     "--reason", "Done", "--decision-source", "owner #1", "--apply",
                     ok=False)
        self.assertTrue(self.source.exists())

    def test_restore_is_byte_exact(self):
        archived = self.archive()
        self.run_cli("restore", archived)
        self.assertFalse(self.source.exists())
        self.run_cli("restore", archived, "--apply")
        self.assertEqual(self.source.read_bytes(), PARTIAL.encode())
        self.assertFalse(archived.exists())
        self.assertIn("restore", (archived.parent / "LOG.md").read_text())

    def test_restore_collision_preserves_both(self):
        archived = self.archive()
        self.source.write_text("other task")
        self.run_cli("restore", archived, "--apply", ok=False)
        self.assertEqual(self.source.read_text(), "other task")
        self.assertTrue(archived.exists())

    def test_crlf_archive_restores_original_bytes(self):
        original = PARTIAL.replace("\n", "\r\n").encode("utf-8")
        self.source.write_bytes(original)
        archived = self.archive()
        self.assertTrue(archived.read_bytes().startswith(original))
        self.run_cli("restore", archived, "--apply")
        self.assertEqual(self.source.read_bytes(), original)

    def test_purge_preserves_original_open_item_markers(self):
        unchecked = "- [ ] 2. Remaining result · [no check]"
        ticked = "- [x] 3. Unproven result · check: test"
        original = PARTIAL.replace("slots: 2", "slots: 3").replace(
            "- [ ] 2. Remaining result · check: test", unchecked + "\n" + ticked)
        self.source.write_text(original, encoding="utf-8")
        archived = self.archive()
        self.run_cli("purge", archived, "--evidence-in", "report #3", "--apply")
        trail = (archived.parent / "LOG.md").read_text()
        self.assertIn(unchecked, trail)
        self.assertIn(ticked, trail)

    def test_purge_requires_evidence_destination_and_saves_trail(self):
        archived = self.archive()
        self.run_cli("purge", archived, "--apply", ok=False)
        self.assertTrue(archived.exists())
        self.run_cli("purge", archived, "--evidence-in", "report #3")
        self.assertFalse((archived.parent / "LOG.md").exists())
        self.run_cli("purge", archived, "--evidence-in", "report #3", "--apply")
        self.assertFalse(archived.exists())
        trail = (archived.parent / "LOG.md").read_text()
        for content in ("Remaining result", "missing output", "report #3", "owner instruction #1"):
            self.assertIn(content, trail)

    def test_archive_directory_link_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.folder / "archive").symlink_to(outside, target_is_directory=True)
        self.run_cli("archive", self.source, "--disposition", "cancelled",
                     "--reason", "Later", "--decision-source", "owner #1", "--apply",
                     ok=False)
        self.assertTrue(self.source.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_links_are_refused(self):
        self.source.rename(self.root / "outside.md")
        self.source.symlink_to(self.root / "outside.md")
        self.run_cli("archive", self.source, "--disposition", "cancelled",
                     "--reason", "Later", "--decision-source", "owner #1", "--apply",
                     ok=False)
        self.source.unlink()
        os.link(self.root / "outside.md", self.source)
        self.run_cli("archive", self.source, "--disposition", "cancelled",
                     "--reason", "Later", "--decision-source", "owner #1", "--apply",
                     ok=False)
        self.assertEqual((self.root / "outside.md").read_text(), PARTIAL)

    def test_linked_disposal_log_preserves_archive(self):
        archived = self.archive()
        outside = self.root / "outside.md"
        outside.write_text("private")
        (archived.parent / "LOG.md").symlink_to(outside)
        self.run_cli("purge", archived, "--evidence-in", "report #3", "--apply", ok=False)
        self.assertTrue(archived.exists())
        self.assertEqual(outside.read_text(), "private")

    def test_completed_validates_slots(self):
        self.source.write_text(PARTIAL.replace("- [ ] 2.", "- [x] 2.").replace(
            "2. Remaining result · check: test", "2. Remaining result · check: test · proof: other.txt"
        ).replace("slots: 2", "slots: 3"))
        self.run_cli("archive", self.source, "--disposition", "completed",
                     "--reason", "Done", "--decision-source", "owner #1", "--apply", ok=False)
        self.assertTrue(self.source.exists())

    def test_corrupt_archive_cannot_be_restored_or_deleted(self):
        archived = self.archive()
        archived.write_bytes(archived.read_bytes().replace(b"First result", b"Other result"))
        self.run_cli("restore", archived, "--apply", ok=False)
        self.run_cli("purge", archived, "--evidence-in", "report #3", "--apply", ok=False)
        self.assertTrue(archived.exists())

    def test_foreign_log_is_not_overwritten(self):
        archived = self.archive()
        log = archived.parent / "LOG.md"
        log.write_text("other content")
        self.run_cli("purge", archived, "--evidence-in", "report #3", "--apply", ok=False)
        self.assertEqual(log.read_text(), "other content")
        self.assertTrue(archived.exists())

    def test_archive_collision_keeps_source(self):
        archived = self.archive()
        original_archive = archived.read_bytes()
        self.source.write_text(PARTIAL)
        self.run_cli("archive", self.source, "--disposition", "cancelled",
                     "--reason", "Other reason", "--decision-source", "owner #2", "--apply", ok=False)
        self.assertEqual(archived.read_bytes(), original_archive)
        self.assertEqual(self.source.read_text(), PARTIAL)

    def test_legacy_and_configured_directories(self):
        self.folder.rename(self.root / ".kanon")
        self.run_cli("archive", self.root / ".kanon/task.md", "--disposition", "cancelled",
                     "--reason", "Later", "--decision-source", "owner #1", "--apply")
        env = dict(os.environ, KANON_DIR="custom")
        (self.root / ".kanon").rename(self.root / "custom")
        result = subprocess.run([sys.executable, str(CLI), "report"], cwd=self.root,
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cancelled", result.stdout)

    def test_write_failure_keeps_original(self):
        with mock.patch("retire.directory", return_value=self.folder), mock.patch(
                "retire.write_new", side_effect=OSError("disk full")):
            rc = retire.main(["archive", str(self.source), "--disposition", "cancelled",
                              "--reason", "Later", "--decision-source", "owner #1", "--apply"])
        self.assertEqual(rc, 1)
        self.assertEqual(self.source.read_text(), PARTIAL)

    def test_trail_failure_keeps_archive(self):
        archived = self.archive()
        with mock.patch("retire.directory", return_value=self.folder), mock.patch(
                "retire.append_trail", side_effect=OSError("disk full")):
            rc = retire.main(["purge", str(archived), "--evidence-in", "report #3", "--apply"])
        self.assertEqual(rc, 1)
        self.assertTrue(archived.exists())

    def test_changed_source_keeps_both_copies(self):
        write = retire.write_new
        def replace_after_write(*args):
            write(*args)
            self.source.write_text("new work")
        with mock.patch("retire.directory", return_value=self.folder), mock.patch(
                "retire.write_new", side_effect=replace_after_write):
            rc = retire.main(["archive", str(self.source), "--disposition", "cancelled",
                              "--reason", "Later", "--decision-source", "owner #1", "--apply"])
        self.assertEqual(rc, 1)
        self.assertEqual(self.source.read_text(), "new work")
        archived = next((self.folder / "archive").glob("*.md"))
        self.assertTrue(archived.read_text().startswith(PARTIAL))

    def test_archive_is_visible_but_does_not_trigger_stop(self):
        self.archive()
        env = dict(os.environ)
        env.pop("KANON_DIR", None)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sweep.py")],
                                cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Archive: 1", result.stdout)
        self.assertIn("archive/", (self.folder / "INDEX.md").read_text())
        for event in ("Stop", "SessionStart"):
            result = subprocess.run([sys.executable, str(ROOT / "hooks/kanon-hook.py"), event],
                                    input="{}", cwd=self.root, env=env, capture_output=True, text=True)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
