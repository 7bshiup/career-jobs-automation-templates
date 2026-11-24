#!/usr/bin/env python3
"""Check the automation templates before anyone imports or submits them (stdlib only).

    python3 project-b/templates/validate.py              # check every template, exit 1 on any problem
    python3 project-b/templates/validate.py --self-test  # prove each check catches a planted fault

Checks:
- every *.json file parses;
- n8n workflows: unique non-empty node ids and names, every connection names existing nodes with a valid
  type and index, a trigger exists, and every non-trigger node is reachable from a trigger;
- credentials are referenced by name only (no credential id, no inline values);
- no token-, key- or secret-looking strings, no placeholders, no instance ids or pinned data anywhere in
  the template folder (JSON and README);
- Apify node input: literal JSON parses, and every input field (literal or in a JSON.stringify expression)
  exists in the actor's input schema;
- each template folder has a README.md with the disclosure line and the per-job price.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT_SCHEMA = HERE.parent / "apify-jobs-actor" / ".actor" / "input_schema.json"
APIFY_NODE = "@apify/n8n-nodes-apify.apify"
DISCLOSURE = "built and sold by the actor's owner"
PRICE = "$0.003"
TEXT_SUFFIXES = {".json", ".md", ".txt"}

SECRET_PATTERNS = [
    ("Apify token", re.compile(r"apify_api_[A-Za-z0-9]{10,}")),
    ("Slack token", re.compile(r"xox[abeoprs]-[A-Za-z0-9-]{10,}")),
    ("Slack webhook URL", re.compile(r"hooks\.slack\.com/services/[A-Za-z0-9/]+")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("Google OAuth token", re.compile(r"ya29\.[0-9A-Za-z_-]{20,}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}")),
    ("token in URL", re.compile(r"[?&](?:token|api_key|apikey|access_token)=(?!\$)[A-Za-z0-9._-]{8,}")),
    ("inline secret value", re.compile(
        r'"(?:token|apiToken|apiKey|api_key|accessToken|access_token|password|secret|clientSecret|'
        r'client_secret|privateKey|private_key)"\s*:\s*"(?!=)[^"]{6,}"', re.I)),
]
PLACEHOLDER = re.compile(  # case-sensitive: prose like "paste the token" is fine, PASTE_TOKEN is not
    r"YOUR[_-](?:API[_-]?)?(?:TOKEN|KEY|SECRET)|PASTE_[A-Z_]+|REPLACE_?ME|CHANGE_?ME|(?i:<your[^>]*>)|"
    r"\bTODO\b|\bFIXME\b|(?i:\bxxxx+\b)|janedoe~")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
LONG_TOKEN = re.compile(r"(?<![A-Za-z0-9_/.-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_/.-])")


def entropy(s: str) -> float:
    counts = Counter(s)
    return -sum(c / len(s) * math.log2(c / len(s)) for c in counts.values())


def scan_text(label: str, text: str) -> list[str]:
    """Secret-looking strings and placeholders in any template file."""
    errors = [f"{label}: {name} found" for name, rx in SECRET_PATTERNS if rx.search(text)]
    for m in PLACEHOLDER.finditer(text):
        errors.append(f"{label}: placeholder {m.group(0)!r} left in")
    for m in LONG_TOKEN.finditer(text):
        tok = m.group(0)
        if not UUID.match(tok) and entropy(tok) > 4.0 and re.search(r"\d", tok) and re.search(r"[A-Za-z]", tok):
            errors.append(f"{label}: high-entropy string {tok[:6]}... looks like a key or document id")
    return errors


def body_fields(body: str) -> tuple[list[str], str | None]:
    """Input field names in an Apify node body: literal JSON or `={{ JSON.stringify({ a: ..., b: ... }) }}`."""
    if not body.startswith("="):
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            return [], f"input JSON does not parse ({e})"
        return (list(data), None) if isinstance(data, dict) else ([], "input JSON is not an object")
    m = re.search(r"JSON\.stringify\(\s*\{(.*)\}\s*\)", body, re.S)
    if not m:
        return [], None  # free-form expression: nothing to check statically
    return re.findall(r"(?:^|,)\s*([A-Za-z_]\w*)\s*:", m.group(1)), None


def check_workflow(label: str, wf: dict, schema_fields: set[str]) -> list[str]:
    errors = []
    nodes, conns = wf.get("nodes"), wf.get("connections")
    if not isinstance(nodes, list) or not nodes:
        return [f"{label}: no nodes list"]
    if not isinstance(conns, dict):
        return [f"{label}: connections is not an object"]
    if wf.get("pinData"):
        errors.append(f"{label}: pinData holds sample data; templates must ship without it")
    if "instanceId" in json.dumps(wf.get("meta") or {}):
        errors.append(f"{label}: meta.instanceId identifies the exporting instance; remove it")

    names, ids = Counter(), Counter()
    for n in nodes:
        for key in ("id", "name", "type", "typeVersion", "position", "parameters"):
            if key not in n or n[key] in ("", None):
                errors.append(f"{label}: node {n.get('name', '?')!r} lacks {key}")
        names[n.get("name")] += 1
        ids[n.get("id")] += 1
    errors += [f"{label}: duplicate node name {k!r}" for k, c in names.items() if c > 1]
    errors += [f"{label}: duplicate node id {k!r}" for k, c in ids.items() if c > 1]

    by_name = {n.get("name"): n for n in nodes}
    edges: dict[str, set[str]] = {}
    for src, outputs in conns.items():
        if src not in by_name:
            errors.append(f"{label}: connection from unknown node {src!r}")
        for ctype, branches in (outputs or {}).items():
            if ctype != "main":
                errors.append(f"{label}: {src!r} uses connection type {ctype!r}")
            for branch in branches or []:
                for c in branch or []:
                    dst = c.get("node")
                    if dst not in by_name:
                        errors.append(f"{label}: {src!r} connects to unknown node {dst!r}")
                    if c.get("type") != "main" or not isinstance(c.get("index"), int) or c["index"] < 0:
                        errors.append(f"{label}: bad connection {src!r} -> {dst!r}: {c}")
                    edges.setdefault(src, set()).add(dst)

    working = {k: n for k, n in by_name.items() if n.get("type") != "n8n-nodes-base.stickyNote"}
    triggers = [k for k, n in working.items() if re.search(r"trigger$|Trigger$|webhook$", str(n.get("type")))]
    if not triggers:
        errors.append(f"{label}: no trigger node")
    reached, todo = set(triggers), list(triggers)
    while todo:
        for nxt in edges.get(todo.pop(), ()):
            if nxt not in reached:
                reached.add(nxt)
                todo.append(nxt)
    errors += [f"{label}: node {k!r} is not reachable from a trigger" for k in working if k not in reached]

    for n in working.values():
        who = f"{label}: node {n.get('name')!r}"
        creds = n.get("credentials")
        if creds is not None:
            if not isinstance(creds, dict):
                errors.append(f"{who}: credentials is not an object")
                creds = {}
            for ctype, ref in creds.items():
                if not isinstance(ref, dict) or set(ref) != {"name"} or not str(ref.get("name", "")).strip():
                    errors.append(f"{who}: credential {ctype!r} must be referenced by name only, got {ref!r}")
        if n.get("type") == APIFY_NODE:
            body = n["parameters"].get("customBody")
            if body is None:
                continue
            fields, err = body_fields(str(body))
            if err:
                errors.append(f"{who}: {err}")
            unknown = [f for f in fields if schema_fields and f not in schema_fields]
            if unknown:
                errors.append(f"{who}: input fields not in the actor's input schema: {unknown}")
    return errors


def check_folder(root: Path) -> tuple[list[str], int]:
    errors, checked = [], 0
    schema_fields = set()
    if INPUT_SCHEMA.exists():
        schema_fields = set(json.loads(INPUT_SCHEMA.read_text())["properties"])
    else:
        errors.append(f"actor input schema not found at {INPUT_SCHEMA}")
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        label = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8")
        errors += scan_text(label, text)
        checked += 1
        if path.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                errors.append(f"{label}: does not parse: {e}")
                continue
            if isinstance(data, dict) and "nodes" in data and "connections" in data:
                errors += check_workflow(label, data, schema_fields)
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        readme = folder / "README.md"
        if not readme.exists():
            errors.append(f"{folder.name}: README.md missing")
            continue
        text = readme.read_text(encoding="utf-8")
        if DISCLOSURE not in text:
            errors.append(f"{folder.name}/README.md: disclosure line ({DISCLOSURE!r}) missing")
        if PRICE not in text:
            errors.append(f"{folder.name}/README.md: price {PRICE} missing")
    return errors, checked


def self_test() -> int:
    """Plant one fault per check in a copy of a good workflow; each must be reported."""
    good_path = next(HERE.glob("n8n-*/workflow.json"))
    good = json.loads(good_path.read_text())
    schema_fields = set(json.loads(INPUT_SCHEMA.read_text())["properties"])
    assert not check_workflow("good", good, schema_fields), check_workflow("good", good, schema_fields)

    def mutated(fn):
        wf = json.loads(json.dumps(good))
        fn(wf)
        return wf

    def first(wf, pred):
        return next(n for n in wf["nodes"] if pred(n))

    apify = lambda n: n["type"] == APIFY_NODE  # noqa: E731
    cases = {
        "dangling connection": mutated(lambda wf: wf["connections"].setdefault("Ghost", {"main": [[{"node": "Nowhere", "type": "main", "index": 0}]]})),
        "duplicate id": mutated(lambda wf: wf["nodes"][-1].update(id=wf["nodes"][-2]["id"])),
        "duplicate name": mutated(lambda wf: wf["nodes"][-1].update(name=wf["nodes"][-2]["name"])),
        "orphan node": mutated(lambda wf: wf["nodes"].append({**first(wf, apify), "id": "x1", "name": "Orphan"})),
        "credential id": mutated(lambda wf: first(wf, lambda n: n.get("credentials"))["credentials"].update(
            apifyApi={"id": "dJAynKkN2pRqy3Ko", "name": "Apify account"})),
        "unknown input field": mutated(lambda wf: first(wf, apify)["parameters"].update(customBody='{"companies": [], "startUrls": []}')),
        "broken input JSON": mutated(lambda wf: first(wf, apify)["parameters"].update(customBody='{"companies": [')),
        "pinned data": mutated(lambda wf: wf.update(pinData={"x": [{"json": {"a": 1}}]})),
    }
    failed = [k for k, wf in cases.items() if not check_workflow(k, wf, schema_fields)]
    text_cases = {
        "Apify token": '{"x": "apify_api_' + "A1b2C3d4E5f6G7h8I9j0" + '"}',
        "Slack token": "xoxb-" + "1234567890-abcdefghij",
        "Slack webhook": "https://hooks.slack.com/services/" + "T000/B000/XXXX",
        "inline secret": '{"apiToken": "' + "s3cr3tvalue99" + '"}',
        "placeholder": "Authorization: Bearer YOUR_TOKEN",
        "channel placeholder": '"value": "PASTE_SLACK_CHANNEL_ID"',
        "sheet id": '"value": "1UjZNjLLpzlGp_noSqp30me6RQw24w1-y-BlX5wg3aOM"',
    }
    failed += [k for k, t in text_cases.items() if not scan_text(k, t)]
    clean = ['"id": "3f1c2b9e-0d4a-4c1b-9a77-2e5d6f8a9b10"', "actor go8YB1qv3eEb4IU4J", "improved_gravity_qb7/greenhouse-lever-ashby-personio-jobs-scraper",
             "create a credential and paste the token; use your token"]
    false_pos = [t for t in clean if scan_text("clean", t)]
    for k in failed:
        print(f"SELF-TEST MISSED: {k}")
    for t in false_pos:
        print(f"SELF-TEST FALSE POSITIVE: {t}")
    print(f"self-test: {len(cases) + len(text_cases) - len(failed)}/{len(cases) + len(text_cases)} planted faults caught, "
          f"{len(false_pos)} false positives")
    return 1 if failed or false_pos else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    errors, checked = check_folder(HERE)
    for e in errors:
        print("FAIL", e)
    print(f"{checked} files checked, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
