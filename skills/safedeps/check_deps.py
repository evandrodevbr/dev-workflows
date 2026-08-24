#!/usr/bin/env python3
"""safedeps: ground an AI coding agent in live OSV.dev vulnerability data.

Queries api.osv.dev (no API key) for real, current advisories on a
package@version -- the data a model's training cutoff cannot have.

API shape verified against https://api.osv.dev on 2026-06-28:
  POST /v1/query       {"package": {"name", "ecosystem"}, "version"} -> {"vulns": [...]}
  POST /v1/querybatch  {"queries": [...]}                              -> {"results": [{"vulns": [{"id","modified"}]}]}
                        (batch results are minimal -- id/modified only, so each
                         hit is re-fetched via GET /v1/vulns/{id} for full detail)
  GET  /v1/vulns/{id}                                                  -> full vuln record

A full vuln record's `affected[].ranges[].events` lists `{"introduced"|"fixed": ...}`
markers; the nearest `fixed` version greater than the queried version is the
upgrade target. `database_specific.severity` (when present) gives HIGH/MODERATE/etc.

Stdlib only: urllib, json, argparse, re.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{}"
TIMEOUT = 15


def _post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _get(url):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


class OSVError(Exception):
    """Network/API failure talking to OSV.dev."""


def query_one(name, version, ecosystem):
    """Query a single package@version. Returns list of full vuln dicts."""
    try:
        data = _post(OSV_QUERY_URL, {"package": {"name": name, "ecosystem": ecosystem}, "version": version})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise OSVError(f"OSV.dev unreachable: {e}") from e
    return data.get("vulns", [])


def query_batch(pkgs):
    """Batch-query [(name, version, ecosystem), ...].

    querybatch returns minimal {id, modified} per hit, so each unique id is
    re-fetched for full details (severity, affected ranges, fixed versions).
    Returns {(name, version, ecosystem): [full_vuln_dict, ...]}.
    """
    queries = [{"package": {"name": n, "ecosystem": e}, "version": v} for n, v, e in pkgs]
    try:
        data = _post(OSV_BATCH_URL, {"queries": queries})
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise OSVError(f"OSV.dev unreachable: {e}") from e

    results = data.get("results", [])
    ids_needed = {v["id"] for r in results for v in r.get("vulns", [])}
    # ponytail: thread pool, not async -- a manifest can carry dozens of unique
    # CVE ids and sequential GETs were timing out (~1s/call * dozens of calls)
    detail_cache = {}
    if ids_needed:
        with ThreadPoolExecutor(max_workers=min(16, len(ids_needed))) as pool:
            futures = {pool.submit(_get, OSV_VULN_URL.format(vid)): vid for vid in ids_needed}
            for future in futures:
                vid = futures[future]
                try:
                    detail_cache[vid] = future.result()
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    raise OSVError(f"OSV.dev unreachable fetching {vid}: {e}") from e

    out = {}
    for (n, v, e), result in zip(pkgs, results):
        ids = [item["id"] for item in result.get("vulns", [])]
        out[(n, v, e)] = [detail_cache[i] for i in ids if i in detail_cache]
    return out


# ---------------------------------------------------------------------------
# Manifest parsing -> list of (ecosystem, name, version)
# ---------------------------------------------------------------------------

def parse_requirements_txt(text):
    deps = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "git+", "http")):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*==\s*([A-Za-z0-9_.\-+]+)", line)
        if m:
            name = m.group(1).split("[")[0]  # drop extras like requests[security]
            deps.append(("PyPI", name, m.group(2)))
    return deps


def parse_package_json(text):
    data = json.loads(text)
    deps = []
    for section in ("dependencies", "devDependencies"):
        for name, spec in data.get(section, {}).items():
            version = re.sub(r"^[\^~>=<\s]+", "", spec)
            if version and version not in ("*", "latest") and not version.startswith(("git", "http", "file:")):
                deps.append(("npm", name, version))
    return deps


def parse_package_lock_json(text):
    """Minimal package-lock.json v2/v3 parser: reads the flat "packages" map."""
    data = json.loads(text)
    deps = []
    for path, meta in data.get("packages", {}).items():
        if not path or "version" not in meta:
            continue
        name = path.rsplit("node_modules/", 1)[-1]
        deps.append(("npm", name, meta["version"]))
    return deps


def parse_go_mod(text):
    deps = []
    in_block = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        m = None
        if in_block:
            m = re.match(r"^([\w./\-]+)\s+(v[\w.\-+]+)", line)
        elif line.startswith("require "):
            m = re.match(r"^require\s+([\w./\-]+)\s+(v[\w.\-+]+)", line)
        if m:
            deps.append(("Go", m.group(1), m.group(2)))
    return deps


PARSERS = {
    "requirements.txt": parse_requirements_txt,
    "package.json": parse_package_json,
    "package-lock.json": parse_package_lock_json,
    "go.mod": parse_go_mod,
}


def parse_manifest(path):
    p = Path(path)
    parser = PARSERS.get(p.name)
    if not parser:
        raise ValueError(f"unrecognized manifest: {p.name} (supported: {', '.join(PARSERS)})")
    return parser(p.read_text())


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _severity(vuln):
    return vuln.get("database_specific", {}).get("severity", "UNKNOWN")


def _version_key(v):
    """Loose dotted-numeric sort key ('v1.2.3' / '1.2.3-rc1' -> (1,2,3,...)).

    Not full semver (no prerelease ordering rules) -- good enough to compare
    versions within one release line, which is all OSV ranges need here.
    """
    v = v.lstrip("vV")
    parts = re.split(r"[.\-+]", v)
    return tuple(int(p) if p.isdigit() else -1 for p in parts)


def _nearest_fixed(vuln, ecosystem_pkg_name, version=None):
    """Fixed version that actually applies to `version`.

    OSV advisories sometimes list multiple disjoint ranges for the same
    package (e.g. a 0.x branch fix and a 1.x branch fix on the same CVE).
    Picking the global-smallest 'fixed' across all ranges can suggest a
    downgrade. When `version` is given, prefer the range whose
    introduced/fixed bracket contains it; otherwise fall back to the
    smallest fixed version >= the queried version, then to the global min.
    """
    candidates = []  # (fixed_str, introduced_str_or_'0')
    for affected in vuln.get("affected", []):
        if affected.get("package", {}).get("name") != ecosystem_pkg_name:
            continue
        for rng in affected.get("ranges", []):
            introduced, fixed = "0", None
            for event in rng.get("events", []):
                if "introduced" in event:
                    introduced = event["introduced"]
                if "fixed" in event:
                    fixed = event["fixed"]
            if fixed:
                candidates.append((fixed, introduced))

    if not candidates:
        return None
    if version is None:
        return sorted(c[0] for c in candidates)[0]

    try:
        vkey = _version_key(version)
        in_range = [
            f for f, intro in candidates
            if _version_key(intro) <= vkey < _version_key(f)
        ]
        if in_range:
            return sorted(in_range, key=_version_key)[0]
        not_lower = [f for f, _ in candidates if _version_key(f) > vkey]
        if not_lower:
            return sorted(not_lower, key=_version_key)[0]
    except (ValueError, TypeError):
        pass
    return sorted(c[0] for c in candidates)[0]


def format_report(name, version, ecosystem, vulns):
    cve_id = lambda v: next((a for a in v.get("aliases", []) if a.startswith("CVE-")), v["id"])
    if not vulns:
        return f"OK    {ecosystem}:{name}@{version} -- no known advisories"

    # OSV mirrors the same CVE from multiple sources (GHSA + NVD); collapse by CVE/id.
    # ponytail: dict keeps first (best-populated GHSA record usually sorts first)
    deduped = list({cve_id(v): v for v in reversed(vulns)}.values())

    lines = [f"VULN  {ecosystem}:{name}@{version} -- {len(deduped)} advisory(ies):"]
    for v in deduped:
        fixed = _nearest_fixed(v, name, version)
        fix_note = f"upgrade to {fixed}" if fixed else "no fixed version published yet"
        summary = v.get("summary") or v.get("details", "")[:100]
        lines.append(f"  - {cve_id(v)} [{_severity(v)}] {summary}")
        lines.append(f"      fix: {fix_note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_pkg_arg(arg):
    """'name@version' or 'name@version:ecosystem' -> (ecosystem, name, version)."""
    if ":" in arg:
        pkg_ver, ecosystem = arg.rsplit(":", 1)
    else:
        pkg_ver, ecosystem = arg, "npm"  # default guess; manifests carry their own ecosystem
    name, _, version = pkg_ver.rpartition("@")
    if not name:
        raise ValueError(f"expected name@version, got: {arg}")
    return ecosystem, name, version


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1

    targets = []  # (ecosystem, name, version)
    for arg in argv:
        if Path(arg).name in PARSERS:
            try:
                targets.extend(parse_manifest(arg))
            except (OSError, ValueError, json.JSONDecodeError) as e:
                print(f"error parsing {arg}: {e}", file=sys.stderr)
                return 1
        else:
            try:
                targets.append(_parse_pkg_arg(arg))
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1

    if not targets:
        print("no dependencies found to check")
        return 0

    try:
        results = query_batch([(n, v, e) for e, n, v in targets])
    except OSVError as e:
        print(f"safedeps: {e} -- skipping vulnerability check (network unavailable)", file=sys.stderr)
        return 2

    any_vuln = False
    for ecosystem, name, version in targets:
        vulns = results.get((name, version, ecosystem), [])
        any_vuln = any_vuln or bool(vulns)
        print(format_report(name, version, ecosystem, vulns))

    return 1 if any_vuln else 0


if __name__ == "__main__":
    sys.exit(main())
