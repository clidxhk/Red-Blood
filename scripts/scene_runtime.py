#!/usr/bin/env python3
"""Offline, curated scene packages. This is a file filter, not a model sandbox.

Only explicitly marked atoms reach an actor; raw sources and global rules never do.
The curator remains responsible for the meaning of each disclosed atom. SHA256
pins entire source files, while line ranges identify the supporting passages.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
REVIEWS = {"tone", "crosslink", "character", "worldbuilding"}
OPAQUE = re.compile(r"[0-9a-f]{16,64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,80}\Z")
MANAGEMENT_FILES = {"agents.md", "claude.md", "memory.md", "readme.md"}


class SceneError(ValueError):
    """An invalid manifest or unsafe request."""


def require(condition, message):
    if not condition:
        raise SceneError(message)


def schema(value, required, optional=(), label="object"):
    require(isinstance(value, dict), f"{label}: expected object")
    require(set(required) <= value.keys(), f"{label}: missing required fields")
    require(value.keys() <= set(required) | set(optional), f"{label}: unknown fields")


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: expected nonempty text")
    return value


def integer(value, label, minimum=None):
    require(type(value) is int, f"{label}: expected integer")
    require(minimum is None or value >= minimum, f"{label}: integer outside range")
    return value


def array(value, label):
    require(isinstance(value, list), f"{label}: expected list")
    return value


def identifier(value, label):
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value), f"{label}: invalid identifier")


def within(path, parent):
    return path == parent or parent in path.parents


def repo_path(root, relative, must_exist=False):
    """Reject ambiguous spellings, traversal, Windows drives/ADS and escaping links."""
    string(relative, "path")
    parts = relative.split("/")
    require(not any(p in ("", ".", "..") for p in parts), "path: invalid component")
    require(not any(c in relative for c in "\\:\x00"), "path: use repository-relative POSIX spelling")
    path = root
    for part in parts:
        require(not part.endswith((" ", ".")), "path: ambiguous component")
        if path.is_dir():
            names = {p.name for p in path.iterdir()}
            if part not in names:
                require(not any(n.casefold() == part.casefold() for n in names), "path: filename case mismatch")
        path = path / part
        require(within(path.resolve(), root), "path: link escapes repository")
    require(not must_exist or path.is_file(), "path: source file does not exist")
    return path


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON: duplicate key")
        result[key] = value
    return result


def formal_content_path(root, relative, must_exist=False):
    """Allow new content directories while excluding management/working files."""
    path = repo_path(root, relative, must_exist=must_exist)
    # Check both the declared spelling and the resolved destination so an
    # in-repository directory link cannot disguise working or management files.
    for candidate in (Path(relative), path.resolve().relative_to(root)):
        require(len(candidate.parts) >= 2 and candidate.suffix.lower() == ".md"
                and candidate.name.casefold() not in MANAGEMENT_FILES
                and candidate.parts[0].casefold() != "scripts"
                and not any(part.startswith(".") for part in candidate.parts),
                "Path must be a formal Markdown content file in a content directory")
    return path


def load_manifest(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=no_duplicate_keys)
    except SceneError:
        raise
    except (OSError, UnicodeError, ValueError) as exc:
        raise SceneError("Cannot read UTF-8 JSON manifest") from exc


def timepoint(point, timeline=None):
    schema(point, {"timeline", "order"}, {"label"}, "time")
    string(point["timeline"], "timeline")
    integer(point["order"], "order")
    if "label" in point:
        string(point["label"], "time label")
    require(timeline is None or point["timeline"] == timeline, "Different timelines cannot be compared")


class Scene:
    def __init__(self, manifest, root=ROOT):
        self.root = Path(root).resolve()
        require(self.root.is_dir(), "Repository root does not exist")
        self.data = copy.deepcopy(manifest)
        self.sources = {}
        self.passages = {}
        self.rules = []
        self._validate()

    def _visibility(self, value, sources=False):
        array(value, "disclose_to")
        allowed = {"director", "writer"}
        if not sources:
            allowed |= {"actor:" + actor for actor in self.actor_ids}
        require(all(isinstance(x, str) and x in allowed for x in value), "Invalid disclosure audience")
        require(len(value) == len(set(value)), "Duplicate disclosure audience")

    def _atom(self, value, event=False):
        if not event:
            schema(value, {"text", "source_ids", "disclose_to"}, label="atom")
        string(value["text"], "atom text")
        refs = array(value["source_ids"], "source_ids")
        require(bool(refs), "Every curated atom needs supporting source IDs")
        require(all(isinstance(x, str) and x in self.sources for x in refs), "Unknown supporting source ID")
        require(len(refs) == len(set(refs)), "Duplicate supporting source ID")
        self._visibility(value["disclose_to"])

    def _validate(self):
        data = self.data
        schema(data, {"version", "scene", "branch", "sources", "actors", "facts", "public_history", "unknowns", "events"}, label="manifest")
        require(type(data["version"]) is int and data["version"] == 1, "Unsupported manifest version")
        scene = data["scene"]
        schema(scene, {"id", "title", "time", "target_paths", "budget_chars", "required_reviews"}, label="scene")
        identifier(scene["id"], "scene id")
        string(scene["title"], "scene title")
        timepoint(scene["time"])
        integer(scene["budget_chars"], "budget_chars", 1)
        targets = array(scene["target_paths"], "target_paths")
        require(bool(targets) and len(targets) == len(set(targets)), "Targets must be nonempty and unique")
        for target in targets:
            formal_content_path(self.root, target)
        required = array(scene["required_reviews"], "required_reviews")
        require(all(isinstance(x, str) and x in REVIEWS for x in required), "Invalid required review")
        require(len(required) == len(set(required)) and {"tone", "crosslink"} <= set(required), "Tone and crosslink reviews are mandatory")
        actors = array(data["actors"], "actors")
        self.actor_ids = set()
        for actor in actors:
            schema(actor, {"id", "name", "persona", "beliefs", "state", "speech_limits"}, label="actor")
            identifier(actor["id"], "actor id")
            require(actor["id"] not in self.actor_ids, "Duplicate actor id")
            self.actor_ids.add(actor["id"])
            string(actor["name"], "actor name")
        require(not actors or "character" in required, "Actors require character review")
        require(len(targets) < 3 or "worldbuilding" in required, "Three or more targets require worldbuilding review")
        branch = data["branch"]
        schema(branch, {"id", "parent"}, label="branch")
        identifier(branch["id"], "branch id")
        if branch["parent"] is not None:
            parent = branch["parent"]
            schema(parent, {"branch_id", "base_event_ids"}, label="branch parent")
            identifier(parent["branch_id"], "parent branch id")
            require(parent["branch_id"] != branch["id"], "Branch cannot parent itself")
            base_ids = array(parent["base_event_ids"], "base_event_ids")
            require(all(isinstance(x, str) for x in base_ids) and len(base_ids) == len(set(base_ids)), "Invalid base event IDs")
        for source in array(data["sources"], "sources"):
            schema(source, {"id", "path", "start_line", "end_line", "sha256", "valid_from", "disclose_to"}, {"valid_until"}, "source")
            sid = source["id"]
            require(isinstance(sid, str) and OPAQUE.fullmatch(sid), "Source IDs must be opaque lowercase hex (16-64 characters)")
            require(sid not in self.sources, "Duplicate source ID")
            self._visibility(source["disclose_to"], sources=True)
            path = repo_path(self.root, source["path"], must_exist=True)
            try:
                raw = path.read_bytes()
                content = raw.decode("utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise SceneError("Cannot read UTF-8 source") from exc
            require(isinstance(source["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]), "Invalid SHA256")
            require(hashlib.sha256(raw).hexdigest() == source["sha256"], "Source SHA256 changed; re-research and repin required")
            start = integer(source["start_line"], "start_line", 1)
            end = integer(source["end_line"], "end_line", start)
            lines = content.splitlines(keepends=True)
            require(end <= len(lines), "Source line range does not exist")
            timeline = scene["time"]["timeline"]
            now = scene["time"]["order"]
            timepoint(source["valid_from"], timeline)
            require(source["valid_from"]["order"] <= now, "Source is not yet valid at scene time")
            if "valid_until" in source:
                timepoint(source["valid_until"], timeline)
                require(source["valid_until"]["order"] >= now, "Source expired before scene time")
            self.sources[sid] = source
            self.passages[sid] = "".join(lines[start - 1:end])
        for group in ("facts", "public_history", "unknowns"):
            for atom in array(data[group], group):
                self._atom(atom)
                if group == "unknowns":
                    require(not any(a.startswith("actor:") for a in atom["disclose_to"]), "Author unknowns cannot be disclosed to actors")
        for actor in actors:
            for group in ("persona", "beliefs", "state", "speech_limits"):
                for atom in array(actor[group], group):
                    self._atom(atom)
                    others = {a for a in atom["disclose_to"] if a.startswith("actor:") and a != "actor:" + actor["id"]}
                    require(not others, "A character card cannot disclose to another actor")
        event_ids = set()
        accepted_ids = set()
        for event in array(data["events"], "events"):
            schema(event, {"id", "order", "branch_id", "status", "text", "source_ids", "disclose_to"}, {"final_source", "reviews"}, "event")
            identifier(event["id"], "event id")
            require(event["id"] not in event_ids, "Duplicate event ID")
            event_ids.add(event["id"])
            integer(event["order"], "event order")
            require(event["order"] <= scene["time"]["order"], "Future event cannot enter scene history")
            require(event["branch_id"] == branch["id"], "Foreign branch event cannot enter this manifest")
            require(event["status"] in ("candidate", "accepted"), "Invalid event status")
            self._atom(event, event=True)
            if event["status"] == "accepted":
                accepted_ids.add(event["id"])
                final = event.get("final_source")
                require(isinstance(final, str) and final in self.sources, "Accepted event needs final prose source")
                formal_content_path(self.root, self.sources[final]["path"], must_exist=True)
                schema(event.get("reviews"), REVIEWS, label="event reviews")
                for review in REVIEWS:
                    expected = "passed" if review in required else "not_applicable"
                    require(event["reviews"][review] == expected, "Accepted event reviews are incomplete or inconsistent with applicability")
            else:
                require("final_source" not in event and "reviews" not in event, "Candidate event cannot carry adoption metadata")
        if branch["parent"] is not None:
            require(set(branch["parent"]["base_event_ids"]) <= accepted_ids, "Branch base must reference retained accepted events")
        self._load_rules(targets)

    def _load_rules(self, targets):
        rule_paths = {"AGENTS.md"}
        for target in targets:
            parent = Path(target).parent
            while parent != Path("."):
                relative = (parent / "AGENTS.md").as_posix()
                path = repo_path(self.root, relative)
                if path.exists():
                    rule_paths.add(relative)
                parent = parent.parent
        for relative in sorted(rule_paths, key=lambda p: (p.count("/"), p)):
            path = repo_path(self.root, relative, must_exist=True)
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise SceneError("Cannot read required rule file") from exc
            self.rules.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "text": text})

    def _disclosed(self, atoms, audience, actor_id=None):
        marker = "actor:" + actor_id if audience == "actor" else audience
        selected = []
        for atom in atoms:
            if audience == "director" or marker in atom["disclose_to"]:
                if audience == "director":
                    selected.append(copy.deepcopy(atom))
                elif audience == "actor":
                    selected.append({"text": atom["text"]})
                else:
                    selected.append({"text": atom["text"], "source_ids": atom["source_ids"]})
        return selected

    def build(self, audience, actor_id=None):
        require(audience in ("director", "writer", "actor"), "Unknown audience")
        require(audience != "actor" or actor_id in self.actor_ids, "Unknown requested actor")
        require(audience == "actor" or actor_id is None, "--actor is only valid with actor audience")
        scene = self.data["scene"]
        package = {"version": 1, "audience": audience}
        if audience != "actor":
            branch = self.data["branch"] if audience == "director" else {"id": self.data["branch"]["id"]}
            package.update({"time": scene["time"], "scene_id": scene["id"], "title": scene["title"], "branch": branch, "rules": self.rules})
            package["sources"] = [dict(s, text=self.passages[sid]) for sid, s in self.sources.items() if audience == "director" or audience in s["disclose_to"]]
        if audience == "director":
            package["scene"] = scene
        for group in ("facts", "public_history", "unknowns"):
            if audience == "actor" and group == "unknowns":
                continue
            package[group] = self._disclosed(self.data[group], audience, actor_id)
        people = []
        for actor in self.data["actors"]:
            if audience == "actor" and actor["id"] != actor_id:
                continue
            card = {"id": actor["id"], "name": actor["name"]}
            for group in ("persona", "beliefs", "state", "speech_limits"):
                card[group] = self._disclosed(actor[group], audience, actor_id)
            # Writer sees only cards with at least one explicitly disclosed atom.
            if audience != "writer" or any(card[g] for g in ("persona", "beliefs", "state", "speech_limits")):
                people.append(card)
        package["actors"] = people
        package["events"] = []
        for event in self.data["events"]:
            visible = self._disclosed([event], audience, actor_id)
            if not visible:
                continue
            if audience == "actor":
                package["events"].extend(visible)
            else:
                item = {k: v for k, v in event.items() if audience == "director" or k != "disclose_to"}
                if audience == "writer" and "final_source" in item and "writer" not in self.sources[item["final_source"]]["disclose_to"]:
                    del item["final_source"]
                package["events"].append(item)
        if audience == "writer":
            # Opaque references may cite hidden provenance, but do not expose its metadata.
            visible_ids = {s["id"] for s in package["sources"]}
            for group in ("facts", "public_history", "unknowns", "events"):
                for atom in package[group]:
                    atom["source_ids"] = [s for s in atom["source_ids"] if s in visible_ids]
            for card in package["actors"]:
                for group in ("persona", "beliefs", "state", "speech_limits"):
                    for atom in card[group]:
                        atom["source_ids"] = [s for s in atom["source_ids"] if s in visible_ids]
        package["budget"] = {"unit": "characters", "limit": scene["budget_chars"], "used": 0}
        while True:
            output = render(package)
            count = len(output)
            if count == package["budget"]["used"]:
                break
            package["budget"]["used"] = count
        require(count <= scene["budget_chars"], "Character budget exceeded; required content was not truncated")
        return output

    def fork(self, branch_id):
        identifier(branch_id, "new branch id")
        require(branch_id != self.data["branch"]["id"], "Fork needs a new branch id")
        result = copy.deepcopy(self.data)
        candidate_refs = {sid for event in result["events"] if event["status"] == "candidate" for sid in event["source_ids"]}
        result["events"] = [e for e in result["events"] if e["status"] == "accepted"]
        result["branch"] = {"id": branch_id, "parent": {"branch_id": self.data["branch"]["id"], "base_event_ids": [e["id"] for e in result["events"]]}}
        for event in result["events"]:
            event["branch_id"] = branch_id
        needed = set()
        for group in ("facts", "public_history", "unknowns"):
            for atom in result[group]:
                needed.update(atom["source_ids"])
        for actor in result["actors"]:
            for group in ("persona", "beliefs", "state", "speech_limits"):
                for atom in actor[group]:
                    needed.update(atom["source_ids"])
        for event in result["events"]:
            needed.update(event["source_ids"])
            needed.add(event["final_source"])
        result["sources"] = [source for source in result["sources"] if source["id"] not in candidate_refs or source["id"] in needed]
        Scene(result, self.root)
        return render(result)


def render(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def write_output(text, output, root, source_paths=(), temp_output_dir=None):
    if output is None:
        sys.stdout.write(text)
        return
    path = Path(output).absolute()
    resolved = path.resolve()
    lexical_runs = root / ".workbench" / "runs"
    runs = lexical_runs.resolve()
    require(runs == lexical_runs, "Output directory cannot redirect through links")
    allowed = within(resolved, runs) and resolved != runs
    if temp_output_dir is not None:
        temporary = Path(temp_output_dir).resolve()
        system_temp = Path(tempfile.gettempdir()).resolve()
        require(temporary.is_dir() and within(temporary, system_temp) and temporary != system_temp and not within(temporary, root) and not within(root, temporary), "Test output directory must be an existing, separate subdirectory of system temp")
        allowed = allowed or (within(resolved, temporary) and resolved != temporary)
    require(allowed, "Output must be under .workbench/runs/ or the explicit temporary test directory")
    require(path == resolved, "Output path cannot redirect through links or traversal")
    require(resolved not in {p.resolve() for p in source_paths}, "Cannot overwrite source or manifest")
    require(not path.exists() and not path.is_symlink(), "Output already exists; overwrite is forbidden")
    require(path.suffix.lower() == ".json", "Output must have .json suffix")
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=".scene-", suffix=".tmp", dir=path.parent, delete=False) as stream:
            staging = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link publication is atomic and cannot replace an existing file.
        os.link(staging, path)
    finally:
        if staging is not None:
            staging.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "build", "fork"):
        sub = commands.add_parser(command)
        sub.add_argument("manifest")
        sub.add_argument("--root", type=Path, default=ROOT)
        if command != "validate":
            sub.add_argument("--output")
            sub.add_argument("--temp-output-dir", type=Path, help="Existing separate directory under OS temp, for tests only")
        if command == "build":
            sub.add_argument("--audience", choices=("director", "writer", "actor"), required=True)
            sub.add_argument("--actor")
        if command == "fork":
            sub.add_argument("--branch-id", required=True)
    args = parser.parse_args(argv)
    private = args.command == "build" and args.audience == "actor"
    try:
        scene = Scene(load_manifest(args.manifest), args.root)
        if args.command == "validate":
            # The director package is the largest mandatory context; validate its budget.
            scene.build("director")
            output = render({"valid": True, "version": 1})
            sys.stdout.write(output)
        else:
            if args.command == "build":
                output = scene.build(args.audience, args.actor)
            else:
                output = scene.fork(args.branch_id)
                Scene(json.loads(output), args.root).build("director")
            source_paths = [repo_path(scene.root, s["path"]) for s in scene.sources.values()]
            write_output(output, args.output, scene.root, source_paths + [Path(args.manifest)], args.temp_output_dir)
        return 0
    except (SceneError, OSError, UnicodeError, TypeError, KeyError, OverflowError, RecursionError) as exc:
        # Never echo a hidden path, identifier, secret content or parser detail to an actor.
        message = "Actor package could not be built; ask the director to validate the manifest." if private else (str(exc) if isinstance(exc, SceneError) else "Request failed; check schema, file access and output path.")
        print("scene_runtime: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
