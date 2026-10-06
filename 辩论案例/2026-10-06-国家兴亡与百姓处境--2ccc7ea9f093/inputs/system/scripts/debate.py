#!/usr/bin/env python3
"""Debate v3.1: local scaffolding, fresh Codex launch, and structural validation.

Python 3.11+. Standard library only. This program does NOT implement the LLM
orchestrator, attest tool events, enforce OS read isolation, or measure truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tomllib
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "3.1"
PHASES = ["foundation", "deep_clash", "evidence_war", "logic_closing", "final_statements"]
ROLES = {"affirmative", "negative", "checker", "judge"}
SYSTEM_FILES = [
    "AGENTS.md", "PROTOCOL.md", "SCHEMA.md", "debate.config.toml",
    ".codex/config.toml", ".agents/skills/evidence-debate/SKILL.md",
    "scripts/debate.py",
] + [f".codex/agents/debate_{role}.toml" for role in sorted(ROLES)]


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def encoded(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def new_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)


def local_path(root: Path, relative: str) -> Path:
    """Reject traversal, absolute paths, and symlinks in managed paths.

    This is a cooperative path check, not a defense against a hostile process
    racing directory replacements and not a sandbox for other Codex tools.
    """
    if not text(relative) or "\\" in relative:
        raise ValueError("Expected a nonempty forward-slash relative path")
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or ":" in relative:
        raise ValueError(f"Unsafe relative path: {relative}")
    root = root.resolve()
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink not allowed: {relative}")
    if not current.resolve().is_relative_to(root):
        raise ValueError(f"Path escapes root: {relative}")
    return current


def parse_topic(source: str) -> str:
    lines = source.lstrip("\ufeff").splitlines()
    if not lines or not lines[0].startswith("【辩题输入】"):
        raise ValueError("PROMPT.md first line must start with 【辩题输入】")
    topic = lines[0].removeprefix("【辩题输入】").strip()
    if not topic or topic in {"在此填写本次辩题", "在此写入您的辩题"}:
        raise ValueError("Replace the topic placeholder in the first line")
    if len(topic) > 4000 or any(unicodedata.category(c).startswith("C") for c in topic):
        raise ValueError("Topic is too long or contains control/format characters")
    return topic


def topic_identity(topic: str) -> tuple[str, str]:
    # Preserve meaning; only Unicode NFC and whitespace are normalized.
    normalized = " ".join(unicodedata.normalize("NFC", topic).split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    title = "".join(c.lower() if c.isalnum() else "-" for c in normalized)
    title = re.sub("-+", "-", title).strip("-")[:28].rstrip("-") or "topic"
    return normalized, f"t-{title}--{digest[:16]}"


def load_config(root: Path) -> dict[str, Any]:
    c = tomllib.loads(local_path(root, "debate.config.toml").read_text(encoding="utf-8"))
    for key in ("planned_rounds", "max_rounds", "extension_rounds", "stable_window", "checkpoint_interval"):
        if not integer(c.get(key)) or c[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if c.get("system_version") != VERSION or not 5 <= c["planned_rounds"] <= c["max_rounds"]:
        raise ValueError("Require v3.1 and 5 <= planned_rounds <= max_rounds")
    ratio = c.get("convergence_start_ratio")
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0 < ratio <= 1:
        raise ValueError("convergence_start_ratio must be in (0, 1]")
    if c.get("purpose") not in {"decision", "hypothesis", "competition"}:
        raise ValueError("Unsupported purpose")
    if c.get("search_policy") not in {"public_only", "offline"}:
        raise ValueError("search_policy must be public_only or offline")
    phase_plan(c["planned_rounds"], c.get("phase_weights"))
    return c


def phase_plan(total: int, weights: Any) -> list[dict[str, Any]]:
    if not integer(total) or total < 5:
        raise ValueError("Five-phase plan needs at least five rounds")
    if not isinstance(weights, list) or len(weights) != 5 or any(not integer(w) or w <= 0 for w in weights):
        raise ValueError("phase_weights requires five positive integers")
    quotas = [total * w / sum(weights) for w in weights]
    counts = [max(1, math.floor(q)) for q in quotas]
    while sum(counts) > total:
        i = max((i for i in range(5) if counts[i] > 1), key=lambda i: counts[i] - quotas[i])
        counts[i] -= 1
    while sum(counts) < total:
        i = max(range(5), key=lambda i: quotas[i] - counts[i])
        counts[i] += 1
    result, first = [], 1
    for name, count in zip(PHASES, counts):
        result.append({"phase": name, "start": first, "end": first + count - 1})
        first += count
    return result


def prepare(root: Path, prompt: str = "PROMPT.md", smoke: bool = False) -> Path:
    root = root.resolve()
    if not local_path(root, ".debate-project").is_file():
        raise ValueError("Not a debate project: missing .debate-project")
    config = load_config(root)
    system_bytes = {name: local_path(root, name).read_bytes() for name in SYSTEM_FILES}
    source = ("【辩题输入】需求不确定时，应先做小型原型还是先完成规格？\n"
              "smoke test: only given assumptions and logical reasoning; no external research.\n"
              if smoke else local_path(root, prompt).read_text(encoding="utf-8-sig"))
    topic = parse_topic(source)
    normalized, key = topic_identity(topic)
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "--" + uuid.uuid4().hex[:12]
    if smoke:
        config.update(planned_rounds=2, max_rounds=2, stable_window=1, search_policy="offline")
        relative = f".smoke/{run_id}"
        plan = [{"phase": "smoke_integration", "start": 1, "end": 2}]
    else:
        topic_root = local_path(root, f"debates/{key}")
        topic_root.mkdir(parents=True, exist_ok=True)
        meta = local_path(root, f"debates/{key}/topic.json")
        try:
            new_text(meta, encoded({"topic_key": key, "normalized_motion": normalized}))
        except FileExistsError:
            old = read_json(meta)
            if old.get("normalized_motion") != normalized:
                raise ValueError("Topic directory collision: refusing to reuse")
        relative = f"debates/{key}/runs/{run_id}"
        plan = phase_plan(config["planned_rounds"], config["phase_weights"])
    run_dir = local_path(root, relative)
    run_dir.mkdir(parents=True, exist_ok=False)
    for folder in ("rounds", "checkpoints", "checks", "evidence", "inputs/system"):
        (run_dir / folder).mkdir(parents=True, exist_ok=False)
    new_text(run_dir / "inputs/PROMPT.md", source)
    hashes = {}
    for name, raw in system_bytes.items():
        dst = run_dir / "inputs/system" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("xb") as stream:
            stream.write(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema_version": VERSION, "run_id": run_id, "topic_key": key,
        "motion_original": topic, "created_at": now.isoformat(), "smoke": smoke,
        "config": config, "initial_plan": plan,
        "convergence_start_round": None if smoke else math.ceil(config["planned_rounds"] * config["convergence_start_ratio"]),
        "system_hashes": hashes,
    }
    new_text(run_dir / "manifest.json", encoded(manifest))
    ledger = {
        "schema_version": VERSION, "run_id": run_id, "execution_mode": "native",
        "status": "prepared", "rounds_completed": 0, "max_rounds": config["max_rounds"],
        "evidence_version": 0, "stop_reason": "", "agents": [], "rounds": [],
        "claims": [], "evidence": [], "issues": [], "coverage": [], "plan_revisions": [],
        "convergence": {}, "final_gate": None, "verdict": None,
        "usage": {"model_calls": None, "tool_calls": None, "tokens": None, "cost": None},
    }
    new_text(run_dir / "run.json", encoded(ledger))
    run_prompt = (
        f"# 本次运行 {run_id}\n\n"
        f"RUN_DIR = {relative}\n\n"
        "这是已经初始化的运行，严禁再次 prepare 或覆盖目录。\n"
        "先读取 RUN_DIR/manifest.json、RUN_DIR/inputs/PROMPT.md、"
        "RUN_DIR/inputs/system/PROTOCOL.md 和 SCHEMA.md，然后执行。\n"
        "以 manifest 的冻结配置为准；不得读取其他辩题或运行。\n"
        "使用真实子 agent，按顺序进行充分交锋、核查、修订、裁决并落盘。\n"
        "若能力缺失，写 blocked 与原因，不伪造结果。\n"
        + ("这是两轮 smoke 集成测试，不联网、不套用正式收敛门槛。\n" if smoke else "")
    )
    new_text(run_dir / "run_prompt.md", run_prompt)
    return run_dir


def validate_run(run_dir: Path) -> list[str]:
    errors: list[str] = []
    try:
        manifest = read_json(run_dir / "manifest.json")
        d = read_json(run_dir / "run.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"Cannot read manifest/ledger: {exc}"]
    if not isinstance(d, dict) or not isinstance(manifest, dict):
        return ["Manifest and ledger must be objects"]

    def need(ok: bool, message: str) -> None:
        if not ok:
            errors.append(message)

    def array(value: Any, label: str) -> list:
        if not isinstance(value, list):
            errors.append(f"{label}: expected array")
            return []
        return value

    def records(value: Any, label: str) -> dict:
        out = {}
        for row in array(value, label):
            if not isinstance(row, dict) or not text(row.get("id")):
                errors.append(f"{label}: object with nonempty id required")
                continue
            need(row["id"] not in out, f"{label}: duplicate id {row['id']}")
            out[row["id"]] = row
        return out

    artifact_paths: set[str] = set()
    def artifact(value: Any, label: str, unique: bool = False) -> None:
        try:
            p = local_path(run_dir, value)
            need(p.is_file() and p.stat().st_size > 0, f"{label}: missing/empty artifact")
            if unique:
                need(value not in artifact_paths, f"{label}: reused round artifact")
                artifact_paths.add(value)
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f"{label}: invalid artifact ({exc})")

    need(d.get("schema_version") == VERSION == manifest.get("schema_version"), "Schema version mismatch")
    need(text(d.get("run_id")) and d.get("run_id") == manifest.get("run_id"), "run_id mismatch")
    need(d.get("execution_mode") == "native", "This project requires native execution")
    need(d.get("status") in {"adjudicated", "inconclusive"}, "Not a final ledger; blocked/prepared/interrupted is not completion")
    config = manifest.get("config", {})
    if not isinstance(config, dict):
        return errors + ["Invalid frozen config"]
    n, limit, version = d.get("rounds_completed"), d.get("max_rounds"), d.get("evidence_version")
    need(integer(n) and integer(limit) and 0 < n <= limit, "Invalid completed/max rounds")
    need(limit == config.get("max_rounds"), "max_rounds differs from frozen configuration")
    need(integer(version) and version >= 0, "Invalid evidence_version")
    need(text(d.get("stop_reason")), "Missing stop_reason")
    for name, expected in manifest.get("system_hashes", {}).items():
        try:
            raw = local_path(run_dir, f"inputs/system/{name}").read_bytes()
            need(hashlib.sha256(raw).hexdigest() == expected, f"Frozen system file changed: {name}")
        except (ValueError, OSError) as exc:
            errors.append(f"Frozen input missing: {name}: {exc}")

    agents = array(d.get("agents"), "agents")
    role_threads = {r: set() for r in ROLES}
    owners = {}
    for a in agents:
        if not isinstance(a, dict):
            errors.append("Invalid agent record")
            continue
        role, tid = a.get("role"), a.get("thread_id")
        need(isinstance(role, str) and role in ROLES, "Invalid role")
        if text(tid) and isinstance(role, str) and role in ROLES:
            need(tid not in owners or owners[tid] == role, "One thread assigned to multiple roles")
            owners[tid] = role
            role_threads[role].add(tid)
        else:
            errors.append("Missing real thread id")
        need(text(a.get("tool_event_ref")), "Missing native tool event locator")
    need(all(role_threads.values()), "All four native roles must be recorded for a final run")

    rounds = array(d.get("rounds"), "rounds")
    need(len(rounds) == n, "Round count differs from round records")
    for expected, r in enumerate(rounds, 1):
        if not isinstance(r, dict):
            errors.append("Invalid round record")
            continue
        need(r.get("number") == expected, "Round numbers must be contiguous")
        need(text(r.get("phase")) and text(r.get("progress_note")), "Round phase/progress missing")
        art = r.get("artifacts", {})
        if not isinstance(art, dict):
            art = {}
        for role in ("affirmative", "negative", "moderator"):
            artifact(art.get(role), f"R{expected}/{role}", unique=True)

    evidence = records(d.get("evidence"), "evidence")
    for eid, e in evidence.items():
        need(text(e.get("locator")), f"{eid}: source locator missing")
        need(e.get("acquisition") in {"observed", "user_supplied", "unobserved"}, f"{eid}: invalid acquisition")
        if e.get("acquisition") == "observed":
            need(text(e.get("tool_event_ref")), f"{eid}: observation locator missing")
    claims = records(d.get("claims"), "claims")
    deps = {}
    for cid, c in claims.items():
        need(text(c.get("text")), f"{cid}: text missing")
        need(c.get("kind") in {"empirical", "logical", "forecast", "value"}, f"{cid}: invalid kind")
        need(isinstance(c.get("decisive"), bool), f"{cid}: decisive must be boolean")
        need(c.get("assessment") in {"supported", "partially_supported", "contradicted", "unverified", "disputed", "not_applicable"}, f"{cid}: invalid assessment")
        es = array(c.get("evidence_ids"), f"{cid}.evidence_ids")
        for eid in es:
            need(isinstance(eid, str) and eid in evidence, f"{cid}: unknown evidence id")
        deps[cid] = []
        for dep in array(c.get("depends_on"), f"{cid}.depends_on"):
            if isinstance(dep, str) and dep in claims:
                deps[cid].append(dep)
            else:
                errors.append(f"{cid}: unknown dependency")
        if c.get("kind") == "empirical" and c.get("assessment") == "supported":
            need(bool(es), f"{cid}: factual support requires evidence")
        if c.get("kind") == "empirical" and c.get("decisive"):
            need(c.get("review_version") == version and text(c.get("review_note")), f"{cid}: decisive fact lacks current review")
    # Check the whole registered graph, including unused claims.
    visited, active = set(), set()
    def visit(cid: str) -> None:
        if cid in active:
            errors.append(f"Dependency cycle: {cid}")
            return
        if cid in visited:
            return
        active.add(cid)
        for dep in deps[cid]:
            visit(dep)
        active.remove(cid)
        visited.add(cid)
    try:
        for cid in claims:
            visit(cid)
    except RecursionError:
        errors.append("Dependency graph too deep")

    for issue in array(d.get("issues"), "issues"):
        if not isinstance(issue, dict):
            errors.append("Invalid issue")
            continue
        for cid in array(issue.get("claim_ids"), "issue.claim_ids"):
            need(isinstance(cid, str) and cid in claims, "Issue references unknown claim")
        need(issue.get("status") in {"open", "resolved", "blocked"}, "Invalid issue status")
    gate, verdict = d.get("final_gate"), d.get("verdict")
    if not isinstance(gate, dict) or not isinstance(verdict, dict):
        return errors + ["Final check and verdict objects required"]
    need(gate.get("evidence_version") == version == verdict.get("evidence_version"), "Stale final check/verdict")
    need(gate.get("checker_thread_id") in role_threads["checker"], "Final check not assigned to checker")
    need(verdict.get("judge_thread_id") in role_threads["judge"], "Verdict not assigned to judge")
    artifact(gate.get("report_path"), "final check")
    artifact(verdict.get("report_path"), "verdict")
    kind = verdict.get("kind")
    need(kind in {"recommendation", "conditional", "inconclusive", "competition_only"}, "Invalid verdict kind")
    need(text(verdict.get("summary")), "Verdict summary missing")
    if kind == "conditional":
        need(bool(verdict.get("conditions")), "Conditional verdict needs conditions")
    roots, blockers = [], set()
    for label in ("relied_claim_ids", "blocking_claim_ids"):
        for cid in array(verdict.get(label), f"verdict.{label}"):
            if not isinstance(cid, str) or cid not in claims:
                errors.append("Verdict references unknown claim")
            elif label == "relied_claim_ids":
                roots.append(cid)
            else:
                blockers.add(cid)
    if kind == "recommendation":
        need(not blockers and bool(roots), "Unconditional recommendation has blockers or no supporting claims")
    if kind == "conditional":
        need(bool(roots), "Conditional verdict must identify supporting/conditional claims")
    seen, pending = set(), list(roots)
    while pending:
        cid = pending.pop()
        if cid in seen:
            continue
        seen.add(cid)
        c = claims[cid]
        need(c.get("assessment") != "contradicted", f"{cid}: contradicted supporting premise")
        if c.get("kind") == "empirical":
            if c.get("assessment") != "supported":
                need(kind in {"conditional", "inconclusive"} and cid in blockers, f"{cid}: unresolved premise not explicitly conditional")
            else:
                need(c.get("review_version") == version, f"{cid}: stale factual review")
                for eid in c.get("evidence_ids", []) if isinstance(c.get("evidence_ids"), list) else []:
                    if isinstance(eid, str) and eid in evidence:
                        need(evidence[eid].get("acquisition") != "unobserved", f"{cid}: unobserved support")
        pending.extend(deps.get(cid, []))

    stop = d.get("stop_reason")
    if stop == "converged":
        c = d.get("convergence", {})
        if not isinstance(c, dict):
            c = {}
        for key in ("coverage_complete", "key_facts_checked", "strongest_objections_addressed", "reverse_case_done", "no_high_value_next_step"):
            need(c.get(key) is True, f"Convergence gate missing: {key}")
        need(integer(n) and integer(manifest.get("convergence_start_round")) and n >= manifest["convergence_start_round"], "Premature normal convergence")
        stable = c.get("stable_rounds")
        need(integer(stable) and integer(n) and config.get("stable_window", 4) <= stable <= n, "Stable window not satisfied")
        need(bool(d.get("coverage")), "Convergence requires coverage records")
        for issue in d.get("issues", []) if isinstance(d.get("issues"), list) else []:
            if isinstance(issue, dict) and issue.get("priority") in {"decisive", "important"}:
                need(issue.get("status") != "open", "Important issue still open at convergence")
    elif stop == "exception_proven":
        need(text(d.get("exception_note")), "Early exception needs explanation")
        eids = array(d.get("exception_evidence_ids"), "exception_evidence_ids")
        need(bool(eids) and all(isinstance(e, str) and e in evidence for e in eids), "Early proof needs evidence")
    elif stop == "smoke_completed":
        need(manifest.get("smoke") is True and n == 2, "smoke_completed is only valid for two-round smoke runs")
    elif stop not in {"budget_exhausted", "evidence_blocked", "user_stopped"}:
        errors.append("Unsupported final stop_reason")
    artifact("final.md", "final.md")
    artifact("full_transcript.md", "full_transcript.md")
    return errors


def launch(root: Path, run_dir: Path, resume: bool = False) -> int:
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("codex not found on PATH; directory is preserved; use a working Codex client")
    manifest = read_json(run_dir / "manifest.json")
    if resume:
        for name, digest in manifest["system_hashes"].items():
            if hashlib.sha256(local_path(root, name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"System config changed since this run: {name}; restore matching version before resuming")
    relative = run_dir.relative_to(root).as_posix()
    prompt = (
        f"读取 {relative}/run_prompt.md 并执行。当前 run_dir 已创建，不要再次 prepare。"
        + ("这是恢复当前运行：先读 run.json 和最近 checkpoint，核对原线程与快照后继续。" if resume else "这是新会话，只处理该运行。")
    )
    # A fresh invocation, not `resume --last`, `fork`, shell interpolation or eval.
    return subprocess.call([executable, "--cd", str(root), prompt], cwd=root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "start"):
        p = sub.add_parser(name)
        p.add_argument("--prompt", default="PROMPT.md")
        p.add_argument("--smoke", action="store_true")
    p = sub.add_parser("plan")
    p.add_argument("--rounds", type=int)
    for name in ("validate", "resume"):
        p = sub.add_parser(name)
        p.add_argument("run_dir")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.command in {"prepare", "start"}:
            run_dir = prepare(root, args.prompt, args.smoke)
            print(encoded({"run_dir": run_dir.relative_to(root).as_posix(), "status": "prepared"}), flush=True)
            return launch(root, run_dir) if args.command == "start" else 0
        if args.command == "plan":
            config = load_config(root)
            total = args.rounds if args.rounds is not None else config["planned_rounds"]
            print(encoded(phase_plan(total, config["phase_weights"])))
            return 0
        run_dir = local_path(root, args.run_dir)
        if args.command == "resume":
            return launch(root, run_dir, resume=True)
        errors = validate_run(run_dir)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: registered structure/files only; not truth, authentic native execution, or OS isolation.")
        return 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
