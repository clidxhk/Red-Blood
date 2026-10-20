"""Safety and provenance regression tests; all fixtures live under OS temp."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scene_runtime import Scene, SceneError, main, write_output


SCRIPT = Path(__file__).with_name("scene_runtime.py")
PUBLIC = "1" * 16
PRIVATE = "2" * 16
FINAL = "3" * 16
CANDIDATE = "4" * 16


class SceneRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="scene-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        self.output_dir = Path(self.tmp.name) / "output"
        self.output_dir.mkdir()
        self.write("AGENTS.md", "ROOT FULL RULE\nSecond rule line\n")
        self.write("stories/AGENTS.md", "STORIES FULL RULE\n")
        self.write("stories/scenes/AGENTS.md", "SCENES FULL RULE\n")
        self.write("lore/public.md", "Known arrival\nUnselected source line\n")
        self.write("lore/hidden-truth.json", '{"truth":"RAW_SECRET_TRUTH","private_key":"HIDDEN_SEMANTIC_KEY"}\n')
        self.write("stories/final.md", "Approved final prose\n")
        self.write(".workbench/runs/proposal.md", "ABANDONED_CANDIDATE_SOURCE\n")
        self.manifest = {
            "version": 1,
            "scene": {
                "id": "scene-1", "title": "DIRECTOR_SCENE_TITLE",
                "time": {"timeline": "local", "order": 20, "label": "evening"},
                "target_paths": ["stories/scenes/new.md"], "budget_chars": 100000,
                "required_reviews": ["tone", "crosslink", "character"],
            },
            "branch": {"id": "DIRECTOR_BRANCH", "parent": None},
            "sources": [self.source(PUBLIC, "lore/public.md", ["writer"]), self.source(PRIVATE, "lore/hidden-truth.json", [])],
            "actors": [
                {"id": "a", "name": "A", "persona": [self.atom("Curated patient persona", ["actor:a", "writer"], PRIVATE)], "beliefs": [self.atom("I believe the guest is friendly", ["actor:a"])], "state": [self.atom("I am waiting", ["actor:a"])], "speech_limits": [self.atom("Keep my own plan private", ["actor:a"])]},
                {"id": "b", "name": "OTHER_CHARACTER_SECRET_NAME", "persona": [self.atom("OTHER_CHARACTER_SECRET_CARD", ["actor:b"])], "beliefs": [], "state": [], "speech_limits": []},
            ],
            "facts": [self.atom("Public gate is open", ["writer", "actor:a"]), self.atom("AUTHOR_ONLY_WORLD_TRUTH", [], PRIVATE)],
            "public_history": [self.atom("The guest arrived", ["actor:a", "actor:b", "writer"])],
            "unknowns": [self.atom("AUTHOR_ONLY_UNRESOLVED_TRUTH", [], PRIVATE)],
            "events": [],
        }

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def source(self, sid, path, audiences):
        return {"id": sid, "path": path, "start_line": 1, "end_line": 1, "sha256": hashlib.sha256((self.root / path).read_bytes()).hexdigest(), "valid_from": {"timeline": "local", "order": 0}, "disclose_to": audiences}

    def atom(self, text, audiences, sid=PUBLIC):
        return {"text": text, "source_ids": [sid], "disclose_to": audiences}

    def candidate(self, event_id="proposal"):
        return dict(self.atom("Candidate dialogue", ["actor:a", "writer"]), id=event_id, order=20, branch_id="DIRECTOR_BRANCH", status="candidate")

    def accepted(self):
        self.manifest["sources"].append(self.source(FINAL, "stories/final.md", []))
        event = dict(self.atom("Accepted starting point", ["writer"]), id="accepted-start", order=10, branch_id="DIRECTOR_BRANCH", status="accepted", final_source=FINAL, reviews={"tone": "passed", "crosslink": "passed", "character": "passed", "worldbuilding": "not_applicable"})
        self.manifest["events"].append(event)
        return event

    def run_cli(self, *args):
        manifest = self.output_dir / "manifest-input.json"
        manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        return subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), *args[:1], str(manifest), "--root", str(self.root), *args[1:]], capture_output=True, text=True, encoding="utf-8")

    def directory_link(self, link, target):
        try:
            link.symlink_to(target, target_is_directory=True)
            self.addCleanup(link.unlink)
            return
        except OSError:
            if os.name != "nt":
                self.skipTest("Directory links unavailable")
        # Windows junctions exercise the same resolved containment check without
        # the Create Symbolic Links privilege or Developer Mode.
        env = dict(os.environ, SCENE_TEST_LINK=str(link), SCENE_TEST_TARGET=str(target))
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", "New-Item -ItemType Junction -Path $env:SCENE_TEST_LINK -Target $env:SCENE_TEST_TARGET -ErrorAction Stop | Out-Null"], capture_output=True, env=env)
        if result.returncode:
            self.skipTest("Neither symlinks nor junctions available")
        self.addCleanup(link.rmdir)

    def test_actor_receives_only_own_explicitly_disclosed_curated_information(self):
        text = Scene(self.manifest, self.root).build("actor", "a")
        package = json.loads(text)
        for secret in ("RAW_SECRET_TRUTH", "HIDDEN_SEMANTIC_KEY", "hidden-truth", "AUTHOR_ONLY", "OTHER_CHARACTER", "DIRECTOR_BRANCH", "DIRECTOR_SCENE_TITLE", "ROOT FULL RULE", PUBLIC, PRIVATE, "source_ids", "sources", "unknowns"):
            self.assertNotIn(secret, text)
        self.assertEqual(len(package["actors"]), 1)
        card = package["actors"][0]
        self.assertEqual(card["persona"], [{"text": "Curated patient persona"}])
        self.assertEqual(card["speech_limits"], [{"text": "Keep my own plan private"}])
        self.assertEqual(card["beliefs"], [{"text": "I believe the guest is friendly"}])
        self.assertNotIn("I believe", str(package["facts"]))

    def test_writer_does_not_receive_director_only_source_metadata_or_text(self):
        text = Scene(self.manifest, self.root).build("writer")
        for hidden in ("RAW_SECRET_TRUTH", "HIDDEN_SEMANTIC_KEY", "hidden-truth", PRIVATE, "OTHER_CHARACTER_SECRET_CARD", "AUTHOR_ONLY"):
            self.assertNotIn(hidden, text)
        self.assertIn("Curated patient persona", text)
        self.assertNotIn("Unselected source line", text)
        self.assertIn("Known arrival", text)

    def test_actor_global_time_and_scene_metadata_cannot_bypass_disclosure(self):
        self.manifest["scene"]["time"] = {"timeline": "SECRET_TIMELINE_NAME", "order": 20, "label": "SECRET_TIME_LABEL"}
        for source in self.manifest["sources"]:
            source["valid_from"]["timeline"] = "SECRET_TIMELINE_NAME"
        text = Scene(self.manifest, self.root).build("actor", "a")
        package = json.loads(text)
        for key in ("time", "title", "scene_id", "target_paths", "scene", "branch"):
            self.assertNotIn(key, package)
        for secret in ("SECRET_TIMELINE_NAME", "SECRET_TIME_LABEL", "DIRECTOR_SCENE_TITLE", "scene-1", "stories/scenes/new.md"):
            self.assertNotIn(secret, text)

    def test_writer_branch_parent_cannot_leak_hidden_event_identifiers(self):
        event = self.accepted()
        event["id"] = "SECRET_BASE_EVENT_ID"
        event["disclose_to"] = []
        self.manifest["branch"]["parent"] = {"branch_id": "SECRET_PARENT_BRANCH", "base_event_ids": [event["id"]]}
        scene = Scene(self.manifest, self.root)
        writer_text = scene.build("writer")
        self.assertEqual(json.loads(writer_text)["branch"], {"id": "DIRECTOR_BRANCH"})
        self.assertNotIn("SECRET_BASE_EVENT_ID", writer_text)
        self.assertNotIn("SECRET_PARENT_BRANCH", writer_text)
        self.assertNotIn("base_event_ids", writer_text)
        director_text = scene.build("director")
        self.assertIn("SECRET_BASE_EVENT_ID", director_text)
        self.assertIn("SECRET_PARENT_BRANCH", director_text)

    def test_director_and_writer_get_complete_rules_along_target_path(self):
        for audience in ("director", "writer"):
            package = json.loads(Scene(self.manifest, self.root).build(audience))
            self.assertEqual([r["path"] for r in package["rules"]], ["AGENTS.md", "stories/AGENTS.md", "stories/scenes/AGENTS.md"])
            self.assertEqual(package["rules"][0]["text"], "ROOT FULL RULE\nSecond rule line\n")
        self.assertIn("RAW_SECRET_TRUTH", Scene(self.manifest, self.root).build("director"))

    def test_world_background_layout_preserves_rules_and_accepted_provenance(self):
        world_rules = "世界目录规则全文\n世界目录第二条\n"
        background_rules = "背景类别规则全文\n背景类别第二条\n"
        self.write("世界/AGENTS.md", world_rules)
        self.write("世界/背景/AGENTS.md", background_rules)
        final_path = "世界/背景/已审定正文.md"
        self.write(final_path, "已审定的背景正文\n")
        self.manifest["scene"]["target_paths"] = ["世界/背景/新设定.md"]
        self.accepted()
        self.manifest["sources"][-1] = self.source(FINAL, final_path, ["writer"])
        scene = Scene(self.manifest, self.root)
        expected_rules = {
            "AGENTS.md": "ROOT FULL RULE\nSecond rule line\n",
            "世界/AGENTS.md": world_rules,
            "世界/背景/AGENTS.md": background_rules,
        }
        for audience in ("director", "writer"):
            with self.subTest(audience=audience):
                package = json.loads(scene.build(audience))
                self.assertEqual({r["path"]: r["text"] for r in package["rules"]}, expected_rules)
                final_source = next(s for s in package["sources"] if s["id"] == FINAL)
                self.assertEqual(final_source["path"], final_path)
                self.assertEqual(final_source["text"], "已审定的背景正文\n")
                self.assertEqual(package["events"][0]["status"], "accepted")
                self.assertEqual(package["events"][0]["final_source"], FINAL)

    def test_budget_counts_complete_serialized_characters_and_never_truncates(self):
        text = Scene(self.manifest, self.root).build("director")
        self.assertEqual(json.loads(text)["budget"]["used"], len(text))
        self.manifest["scene"]["budget_chars"] = 10
        with self.assertRaisesRegex(SceneError, "budget"):
            Scene(self.manifest, self.root).build("director")

    def test_changed_unselected_line_invalidates_whole_file_hash(self):
        self.write("lore/public.md", "Known arrival\nChanged outside selected passage\n")
        with self.assertRaisesRegex(SceneError, "SHA256 changed"):
            Scene(self.manifest, self.root)

    def test_line_range_must_exist(self):
        self.manifest["sources"][0]["end_line"] = 999
        with self.assertRaisesRegex(SceneError, "line range"):
            Scene(self.manifest, self.root)

    def test_timelines_are_not_numerically_compared(self):
        for bound in ("valid_from", "valid_until"):
            with self.subTest(bound=bound):
                data = copy.deepcopy(self.manifest)
                data["sources"][0][bound] = {"timeline": "other-calendar", "order": 0 if bound == "valid_from" else 9999}
                with self.assertRaisesRegex(SceneError, "Different timelines"):
                    Scene(data, self.root)

    def test_future_and_expired_sources_are_rejected(self):
        for field, order in (("valid_from", 21), ("valid_until", 19)):
            with self.subTest(field=field):
                data = copy.deepcopy(self.manifest)
                data["sources"][0][field] = {"timeline": "local", "order": order}
                with self.assertRaises(SceneError):
                    Scene(data, self.root)

    def test_unsafe_and_inexact_source_paths_are_rejected(self):
        for path in ("../outside.md", "/absolute.md", "C:/file.md", "lore\\public.md", "lore/./public.md", "Lore/public.md", "lore/public.md:stream"):
            with self.subTest(path=path):
                data = copy.deepcopy(self.manifest)
                data["sources"][0]["path"] = path
                with self.assertRaises(SceneError):
                    Scene(data, self.root)

    def test_directory_link_cannot_escape_root(self):
        link = self.root / "linked"
        self.directory_link(link, self.output_dir)
        (self.output_dir / "outside.md").write_text("outside", encoding="utf-8")
        self.manifest["sources"][0]["path"] = "linked/outside.md"
        with self.assertRaisesRegex(SceneError, "escapes repository"):
            Scene(self.manifest, self.root)

    def test_unknowns_and_other_cards_cannot_be_authorized_to_actor(self):
        for atom in (self.manifest["unknowns"][0], self.manifest["actors"][1]["persona"][0]):
            atom["disclose_to"].append("actor:a")
            with self.assertRaises(SceneError):
                Scene(self.manifest, self.root)
            atom["disclose_to"].pop()

    def test_foreign_branch_future_and_duplicate_events_fail(self):
        for mutation in ("foreign", "future", "duplicate"):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(self.manifest)
                event = self.candidate()
                if mutation == "foreign":
                    event["branch_id"] = "unaccepted-alternative"
                if mutation == "future":
                    event["order"] = 21
                data["events"] = [event, copy.deepcopy(event)] if mutation == "duplicate" else [event]
                with self.assertRaises(SceneError):
                    Scene(data, self.root)

    def test_accepted_event_requires_formal_prose_and_all_applicable_reviews(self):
        event = self.accepted()
        Scene(self.manifest, self.root)
        for field in ("final_source", "reviews"):
            saved = event.pop(field)
            with self.assertRaises(SceneError):
                Scene(self.manifest, self.root)
            event[field] = saved
        event["reviews"]["character"] = "not_applicable"
        with self.assertRaises(SceneError):
            Scene(self.manifest, self.root)
        event["reviews"]["character"] = "passed"
        event["final_source"] = PRIVATE
        with self.assertRaisesRegex(SceneError, "formal Markdown"):
            Scene(self.manifest, self.root)

    def test_review_applicability_cannot_omit_character_or_three_target_check(self):
        self.manifest["scene"]["required_reviews"] = ["tone", "crosslink"]
        with self.assertRaisesRegex(SceneError, "character"):
            Scene(self.manifest, self.root)
        self.manifest["scene"]["required_reviews"].append("character")
        self.manifest["scene"]["target_paths"] += ["stories/second.md", "stories/third.md"]
        with self.assertRaisesRegex(SceneError, "worldbuilding"):
            Scene(self.manifest, self.root)

    def test_formal_targets_reject_management_root_and_working_paths(self):
        rejected = ["README.md", "MEMORY.md", "CLAUDE.md", "AGENTS.md", "root-prose.md", "stories/README.md", "stories/nested/readme.MD", "stories/MEMORY.md", "stories/CLAUDE.md", "stories/AGENTS.md", "scripts/prose.md", ".workbench/runs/prose.md", "stories/.private/prose.md"]
        for target in rejected:
            with self.subTest(target=target):
                data = copy.deepcopy(self.manifest)
                data["scene"]["target_paths"] = [target]
                with self.assertRaisesRegex(SceneError, "formal Markdown"):
                    Scene(data, self.root)
        self.manifest["scene"]["target_paths"] = ["新设目录/新篇正文.md"]
        Scene(self.manifest, self.root)

    def test_accepted_final_source_rejects_management_root_and_working_paths(self):
        self.accepted()
        rejected = ["README.md", "MEMORY.md", "CLAUDE.md", "AGENTS.md", "root-prose.md", "stories/README.md", "stories/nested/readme.MD", "stories/MEMORY.md", "stories/CLAUDE.md", "stories/AGENTS.md", "scripts/prose.md", ".workbench/runs/prose.md", "stories/.private/prose.md"]
        for final_path in rejected:
            with self.subTest(final_path=final_path):
                self.write(final_path, "This is not formal prose\n")
                data = copy.deepcopy(self.manifest)
                data["sources"][-1] = self.source(FINAL, final_path, [])
                with self.assertRaisesRegex(SceneError, "formal Markdown"):
                    Scene(data, self.root)
        final_path = "新设目录/已审定正文.md"
        self.write(final_path, "已审定正文\n")
        self.manifest["sources"][-1] = self.source(FINAL, final_path, [])
        Scene(self.manifest, self.root)

    def test_formal_content_junction_cannot_disguise_workbench_as_prose(self):
        self.directory_link(self.root / "formal_alias", self.root / ".workbench/runs")
        data = copy.deepcopy(self.manifest)
        data["scene"]["target_paths"] = ["formal_alias/proposal.md"]
        with self.assertRaisesRegex(SceneError, "formal Markdown"):
            Scene(data, self.root)
        self.accepted()
        self.manifest["sources"][-1] = self.source(FINAL, "formal_alias/proposal.md", [])
        with self.assertRaisesRegex(SceneError, "formal Markdown"):
            Scene(self.manifest, self.root)

    def test_fork_keeps_accepted_base_and_snapshot_but_removes_candidate_source(self):
        self.accepted()
        event = self.candidate()
        event["source_ids"] = [CANDIDATE]
        self.manifest["sources"].append(self.source(CANDIDATE, ".workbench/runs/proposal.md", []))
        self.manifest["events"].append(event)
        forked = json.loads(Scene(self.manifest, self.root).fork("new-branch"))
        self.assertEqual(forked["actors"], self.manifest["actors"])
        self.assertEqual(forked["facts"], self.manifest["facts"])
        self.assertEqual(forked["branch"]["parent"], {"branch_id": "DIRECTOR_BRANCH", "base_event_ids": ["accepted-start"]})
        self.assertEqual([e["branch_id"] for e in forked["events"]], ["new-branch"])
        self.assertEqual(forked["events"][0]["reviews"], self.manifest["events"][0]["reviews"])
        self.assertNotIn("Candidate dialogue", json.dumps(forked))
        self.assertNotIn("proposal.md", json.dumps(forked))
        Scene(forked, self.root)

    def test_invalid_parent_base_is_rejected(self):
        for parent in ({"branch_id": "DIRECTOR_BRANCH", "base_event_ids": []}, {"branch_id": "other", "base_event_ids": ["missing"]}, {"branch_id": "other", "base_event_ids": ["x", "x"]}):
            self.manifest["branch"]["parent"] = parent
            with self.assertRaises(SceneError):
                Scene(self.manifest, self.root)

    def test_writer_event_omits_hidden_final_source_id(self):
        self.accepted()
        writer = Scene(self.manifest, self.root).build("writer")
        self.assertNotIn(FINAL, writer)
        self.assertNotIn("Approved final prose", writer)

    def test_output_is_nonoverwriting_and_confined(self):
        target = self.root / ".workbench/runs/package.json"
        write_output("{}\n", target, self.root)
        with self.assertRaises(SceneError):
            write_output("replacement", target, self.root)
        self.assertEqual(target.read_text(), "{}\n")
        for forbidden in (self.root / "stories/package.json", self.output_dir / "package.json"):
            with self.assertRaises(SceneError):
                write_output("{}", forbidden, self.root)
            self.assertFalse(forbidden.exists())
        allowed = self.output_dir / "explicit-test.json"
        write_output("{}", allowed, self.root, temp_output_dir=self.output_dir)
        self.assertTrue(allowed.exists())

    def test_output_cannot_redirect_runs_into_formal_content(self):
        workbench = self.root / ".workbench"
        # The fixture already has a real runs directory; use a nested escaping link.
        linked = workbench / "runs" / "redirect"
        self.directory_link(linked, self.root / "stories")
        with self.assertRaises(SceneError):
            write_output("{}", linked / "package.json", self.root)
        self.assertFalse((self.root / "stories/package.json").exists())

    def test_cli_actor_failure_is_generic_and_leaves_no_output(self):
        self.manifest["sources"][1]["sha256"] = "0" * 64
        destination = self.root / ".workbench/runs/failed.json"
        result = self.run_cli("build", "--audience", "actor", "--actor", "a", "--output", str(destination))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.strip(), "scene_runtime: Actor package could not be built; ask the director to validate the manifest.")
        self.assertFalse(destination.exists())
        self.assertEqual(list(destination.parent.glob(".scene-*.tmp")), [])

    def test_cli_budget_failure_leaves_no_partial_file(self):
        self.manifest["scene"]["budget_chars"] = 1
        destination = self.root / ".workbench/runs/over-budget.json"
        result = self.run_cli("build", "--audience", "writer", "--output", str(destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("budget exceeded", result.stderr)
        self.assertFalse(destination.exists())

    def test_cli_actor_oversized_json_integer_fails_without_traceback(self):
        manifest = self.output_dir / "oversized-integer.json"
        manifest.write_text('{"version":' + "1" * 5000 + '}', encoding="utf-8")
        destination = self.root / ".workbench/runs/bad-integer.json"
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "build", str(manifest), "--root", str(self.root), "--audience", "actor", "--actor", "a", "--output", str(destination)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.strip(), "scene_runtime: Actor package could not be built; ask the director to validate the manifest.")
        self.assertFalse(destination.exists())

    def test_cli_validate_build_and_fork_are_read_only_unless_output_is_explicit(self):
        result = self.run_cli("validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])
        result = self.run_cli("build", "--audience", "actor", "--actor", "a")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["audience"], "actor")
        result = self.run_cli("fork", "--branch-id", "alternative")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["branch"]["id"], "alternative")
        self.assertEqual(list((self.root / ".workbench/runs").glob("*.json")), [])

    def test_strict_schema_and_duplicate_json_keys_fail_cleanly(self):
        self.manifest["untracked_candidate_artifacts"] = ["not allowed"]
        result = self.run_cli("validate")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        manifest = self.output_dir / "duplicate.json"
        manifest.write_text('{"version":1,"version":1}', encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT), "validate", str(manifest), "--root", str(self.root)], capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate key", result.stderr)


if __name__ == "__main__":
    unittest.main()
