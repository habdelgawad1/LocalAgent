"""Convert external scanner JSON into LocalAgent's finding format."""
import json
import os
from pathlib import Path


SEVERITIES = {"high", "medium", "low", "info"}


def _read(path):
    try:
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _finding(fid, severity, layer, title, detail, source, path):
    return {
        "id": fid,
        "severity": severity if severity in SEVERITIES else "info",
        "layer": layer,
        "title": title,
        "detail": detail,
        "evidence_seq": [],
        "call_id": None,
        "source": source,
        "evidence_file": os.path.relpath(path).replace(os.sep, "/"),
    }


def pip_audit(path: Path):
    """Adapt pip-audit's JSON report."""
    data = _read(path)
    if not isinstance(data, dict):
        return []
    findings = []
    for dependency in data.get("dependencies", []):
        if not isinstance(dependency, dict):
            continue
        name = dependency.get("name", "unknown package")
        version = dependency.get("version", "unknown version")
        for vuln in dependency.get("vulns", []):
            if not isinstance(vuln, dict):
                continue
            vuln_id = vuln.get("id", "unknown")
            fixes = vuln.get("fix_versions") or []
            detail = f"{name} {version}; fix versions: {', '.join(map(str, fixes)) or 'none listed'}"
            description = vuln.get("description")
            if description:
                detail += f". {description}"
            findings.append(_finding(
                f"pip_audit_{vuln_id}", "medium", "Ecosystem",
                f"Vulnerable dependency: {name}", detail, "pip-audit", path,
            ))
    return findings


def _not_mapped(path, source, layer):
    data = _read(path)
    if data is None:
        return []
    return [_finding(
        f"{source.replace('-', '_')}_output_not_yet_mapped", "info", layer,
        f"{source} output format not yet mapped", "",
        source, path,
    )]


def mcp_scan(path: Path):
    """Adapt mcp-scan JSON; currently reports an explicit unmapped notice."""
    return _not_mapped(path, "mcp-scan", "Tooling")


def mcp_authlab(path: Path):
    """Adapt mcp-authlab JSON; currently reports an explicit unmapped notice."""
    return _not_mapped(path, "mcp-authlab", "Orchestration")


def a2a_scanner(path: Path):
    """Adapt Cisco A2A scanner JSON; currently reports an explicit unmapped notice."""
    return _not_mapped(path, "a2a-scanner", "Orchestration")
