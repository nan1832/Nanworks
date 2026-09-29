#!/usr/bin/env python3
"""Audit or delete exact HPC cleanup candidates from a frozen TSV manifest."""

import argparse
import csv
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Any, Dict, List, Optional, Tuple

PROTECTED_NAMES = {
    "selected_checkpoint.tsv",
    "eval_full.done",
    "train.done",
    "results.json",
    "run_config.json",
}
ALLOWED_ROOTS = (
    Path("/datapool/home/ph_teacher3/Lwy/zhounan/Visedit2"),
    Path("/tmp/ph_teacher3"),
)
CONFIRM_TEXT = "DELETE-EXACT-VALIDATED-MANIFEST"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def read_manifest(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if not rows or not {"path", "reason"}.issubset(rows[0]):
        raise ValueError("manifest must contain path and reason columns")
    for row in rows:
        if not Path(row["path"]).is_absolute():
            raise ValueError(f"manifest path is not absolute: {row['path']}")
        if any(char in row["path"] for char in "*?[]{}\n\r\t"):
            raise ValueError(f"manifest path contains a wildcard/control character: {row['path']}")
    return rows


def active_references(candidates: List[Path]) -> List[Dict[str, str]]:
    proc = Path("/proc")
    if os.name != "posix" or not proc.is_dir():
        return []
    refs = []  # type: List[Dict[str, str]]
    self_pid = os.getpid()
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == self_pid:
            continue
        pid = entry.name
        targets = []  # type: List[Tuple[str, str]]
        for kind, link in (("cwd", entry / "cwd"), ("exe", entry / "exe")):
            try:
                targets.append((kind, os.path.realpath(link)))
            except OSError:
                pass
        try:
            for fd in (entry / "fd").iterdir():
                try:
                    targets.append(("fd", os.path.realpath(fd)))
                except OSError:
                    pass
        except OSError:
            pass
        try:
            cmd = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "ignore")
        except OSError:
            cmd = ""
        for candidate in candidates:
            prefix = str(candidate)
            for kind, target in targets:
                target_path = Path(target)
                if target == prefix or within(target_path, candidate):
                    refs.append({"pid": pid, "kind": kind, "target": target, "candidate": prefix})
            if prefix in cmd:
                refs.append({"pid": pid, "kind": "cmd", "target": cmd, "candidate": prefix})
    return refs


def scan_candidate(path: Path, current_user: str) -> Dict[str, Any]:
    entries = files = bytes_seen = foreign = symlinks = 0
    protected = []  # type: List[str]

    def inspect(item: Path) -> None:
        nonlocal entries, files, bytes_seen, foreign, symlinks
        info = item.lstat()
        entries += 1
        bytes_seen += info.st_size
        if stat.S_ISREG(info.st_mode):
            files += 1
        if stat.S_ISLNK(info.st_mode):
            symlinks += 1
        if item.name in PROTECTED_NAMES:
            protected.append(str(item))
        if os.name == "posix":
            try:
                import pwd

                owner = pwd.getpwuid(info.st_uid).pw_name
                if owner != current_user:
                    foreign += 1
            except (KeyError, ImportError):
                foreign += 1

    inspect(path)
    if path.is_dir():
        for base, dirs, names in os.walk(path, followlinks=False):
            for name in dirs + names:
                inspect(Path(base) / name)
    return {
        "path": str(path),
        "entries": entries,
        "files": files,
        "apparent_bytes": bytes_seen,
        "foreign_owned": foreign,
        "symlinks": symlinks,
        "protected_markers": protected,
    }


def run_audit(root: Path, rows: List[Dict[str, str]], scope_profile: str) -> Dict[str, Any]:
    violations = []  # type: List[str]
    root = root.resolve(strict=True)
    if scope_profile == "visedit2" and not any(root == allowed or within(root, allowed) for allowed in ALLOWED_ROOTS):
        violations.append(f"root outside VisEdit2 scope: {root}")

    candidates = []  # type: List[Path]
    details = []  # type: List[Dict[str, Any]]
    current_user = getpass.getuser()
    for row in rows:
        raw = Path(row["path"])
        if not raw.exists() and not raw.is_symlink():
            violations.append(f"missing candidate: {raw}")
            continue
        if raw.is_symlink():
            violations.append(f"candidate root is symlink: {raw}")
            continue
        resolved = raw.resolve(strict=True)
        if resolved == root or not within(resolved, root):
            violations.append(f"candidate escapes/equal root: {raw} -> {resolved}")
            continue
        candidates.append(resolved)
        detail = scan_candidate(resolved, current_user)
        detail["reason"] = row["reason"]
        details.append(detail)
        if detail["foreign_owned"]:
            violations.append(f"foreign-owned entries in {resolved}: {detail['foreign_owned']}")
        if detail["symlinks"]:
            violations.append(f"symlinks in {resolved}: {detail['symlinks']}")
        if detail["protected_markers"]:
            violations.append(f"protected markers in {resolved}: {len(detail['protected_markers'])}")

    for index, left in enumerate(candidates):
        for right in candidates[index + 1 :]:
            if left == right or within(left, right) or within(right, left):
                violations.append(f"overlapping candidates: {left} <> {right}")

    refs = active_references(candidates)
    if refs:
        violations.append(f"active process references: {len(refs)}")
    return {
        "root": str(root),
        "scope_profile": scope_profile,
        "current_user": current_user,
        "candidate_count": len(rows),
        "details": details,
        "active_references": refs,
        "violations": violations,
    }


def write_json(path: Optional[Path], payload: Dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        sys.stdout.write(text)
        return
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def delete_candidates(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    deleted = []  # type: List[Dict[str, str]]
    paths = sorted((Path(row["path"]).resolve(strict=True), row["reason"]) for row in rows)
    for path, reason in sorted(paths, key=lambda item: len(item[0].parts), reverse=True):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        if path.exists() or path.is_symlink():
            raise RuntimeError(f"deletion verification failed: {path}")
        deleted.append({"path": str(path), "reason": reason, "status": "deleted"})
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--mode", choices=("audit", "delete"), default="audit")
    parser.add_argument("--scope-profile", choices=("visedit2", "test"), default="visedit2")
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--audit-report", type=Path)
    parser.add_argument("--delete-log", type=Path)
    parser.add_argument("--confirm-sha256")
    parser.add_argument("--confirm-text")
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    manifest_hash = sha256_file(args.manifest)
    audit = run_audit(args.root, rows, args.scope_profile)
    audit["manifest"] = str(args.manifest.resolve())
    audit["manifest_sha256"] = manifest_hash

    if args.mode == "audit":
        write_json(args.audit_output, audit)
        return 0 if not audit["violations"] else 2

    if not args.audit_report or not args.audit_report.is_file():
        raise ValueError("delete mode requires --audit-report")
    prior = json.loads(args.audit_report.read_text(encoding="utf-8"))
    if prior.get("manifest_sha256") != manifest_hash or prior.get("violations"):
        raise ValueError("frozen audit is missing, stale, or contains violations")
    if args.confirm_sha256 != manifest_hash or args.confirm_text != CONFIRM_TEXT:
        raise ValueError("delete confirmation does not match the frozen manifest")
    if audit["violations"]:
        write_json(args.delete_log, {"status": "blocked", "audit": audit})
        return 2

    deleted = delete_candidates(rows)
    write_json(args.delete_log, {"status": "complete", "manifest_sha256": manifest_hash, "deleted": deleted})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
