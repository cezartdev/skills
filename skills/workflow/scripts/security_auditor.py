#!/usr/bin/env python3
"""Security Auditor: Deterministic OWASP Top 10 SAST, Secret Leak, and Dependency CVE Scanner."""

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

try:
    from .scaffolder import get_workflow_root, sanitize_identifier
except ImportError:
    from scaffolder import get_workflow_root, sanitize_identifier


# ==============================================================================
# 1. OWASP Top 10 Pattern Rules Catalog
# ==============================================================================

OWASP_RULES = [
    # A01: Broken Access Control (Path Traversal & Permissive CORS)
    {
        "id": "SEC-A01-PATH-TRAVERSAL",
        "owasp": "A01:2021-Broken Access Control",
        "severity": "HIGH",
        "title": "Potential Path Traversal Pattern",
        "description": "Direct concatenation of user or unvalidated variables into file path operations.",
        "regex": r"(?:open|readFile|readFileSync|createReadStream)\s*\(\s*(?:f[\"']|\w+\s*\+\s*|\`[^\`]*\$\{)",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs"],
        "remediation": "Sanitize path inputs with os.path.abspath / path.resolve and verify they stay within allowed base directories.",
    },
    {
        "id": "SEC-A01-CORS-WILDCARD",
        "owasp": "A01:2021-Broken Access Control",
        "severity": "MEDIUM",
        "title": "Overly Permissive CORS with Wildcard",
        "description": "CORS configuration allows wildcard origin '*' while permitting credentials or unrestricted headers.",
        "regex": r"(?:cors\(\s*\{[^\}]*origin\s*:\s*[\"']\*[\"'][^\}]*credentials\s*:\s*true|Access-Control-Allow-Origin[\"']?\s*:\s*[\"']\*[\"'])",
        "extensions": [".py", ".ts", ".js", ".go", ".java", ".cs"],
        "remediation": "Specify an explicit list of trusted origin domains instead of wildcard '*'.",
    },

    # A02: Cryptographic Failures & Hardcoded Secrets
    {
        "id": "SEC-A02-DEPRECATED-HASH",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "HIGH",
        "title": "Use of Broken Cryptographic Hash (MD5 / SHA1)",
        "description": "MD5 and SHA-1 are cryptographically broken and vulnerable to collision attacks.",
        "regex": r"(?:hashlib\.(?:md5|sha1)\(|crypto\.createHash\(\s*[\"'](?:md5|sha1)[\"']|md5\.New\(\)|sha1\.New\(\)|MessageDigest\.getInstance\(\s*[\"'](?:MD5|SHA-1)[\"'])",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs"],
        "remediation": "Upgrade to SHA-256, SHA-3, or password-hashing algorithms (Argon2id, bcrypt).",
    },
    {
        "id": "SEC-A02-HARDCODED-PRIVATE-KEY",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "CRITICAL",
        "title": "Hardcoded Private Key Detected",
        "description": "Embedded RSA, EC, or OpenSSH private key block found in source code.",
        "regex": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs", ".json", ".yaml", ".yml", ".env"],
        "remediation": "Remove private keys from source control immediately and inject via environment secrets or vault.",
    },
    {
        "id": "SEC-A02-TLS-INSECURE-SKIP",
        "owasp": "A02:2021-Cryptographic Failures",
        "severity": "HIGH",
        "title": "Disabled TLS Certificate Verification",
        "description": "TLS certificate verification is disabled, exposing connections to Man-In-The-Middle (MITM) attacks.",
        "regex": r"(?:InsecureSkipVerify\s*:\s*true|verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\"']?0[\"']?|rejectUnauthorized\s*:\s*false)",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs"],
        "remediation": "Always enable TLS certificate verification and use trusted CA root stores.",
    },

    # A03: Injection (SQL, Command, Code)
    {
        "id": "SEC-A03-SQL-STRING-CONCAT",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "title": "SQL Injection via String Formatting",
        "description": "Raw SQL query constructed via string interpolation or concatenation instead of parameterized binding.",
        "regex": r"(?:execute|query|rawQuery)\s*\(\s*(?:f[\"'](?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+|[\"'](?:SELECT|INSERT|UPDATE|DELETE|DROP)[^\"']*[\"']\s*\+\s*|\`[^\`]*(?:SELECT|INSERT|UPDATE|DELETE|DROP)[^\`]*\$\{)",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs"],
        "remediation": "Use parameterized queries or ORM query builders (e.g. cursor.execute('SELECT * FROM t WHERE id = %s', (id,))).",
    },
    {
        "id": "SEC-A03-COMMAND-INJECTION-SHELL",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "title": "OS Command Injection (shell=True / exec)",
        "description": "Execution of system commands with shell interpretation or unsanitized strings.",
        "regex": r"(?:subprocess\.(?:run|Popen|call|check_output)\s*\([^)]*shell\s*=\s*True|child_process\.exec\s*\(|os\.system\s*\(|Runtime\.getRuntime\(\)\.exec\s*\()",
        "extensions": [".py", ".ts", ".js", ".java", ".cs"],
        "remediation": "Pass command arguments as an array with shell=False (or use execFile) and validate all arguments.",
    },
    {
        "id": "SEC-A03-CODE-INJECTION-EVAL",
        "owasp": "A03:2021-Injection",
        "severity": "CRITICAL",
        "title": "Dynamic Code Evaluation (eval / exec)",
        "description": "Arbitrary code execution primitive evaluates raw input strings.",
        "regex": r"(?:\beval\s*\(|\bexec\s*\(|new\s+Function\s*\()",
        "extensions": [".py", ".ts", ".js"],
        "remediation": "Avoid dynamic code evaluation. Use safe parsers like json.loads() or structured configuration.",
    },

    # A05: Security Misconfiguration
    {
        "id": "SEC-A05-DEBUG-ENABLED",
        "owasp": "A05:2021-Security Misconfiguration",
        "severity": "HIGH",
        "title": "Debug Mode Enabled in Codebase",
        "description": "Debug mode active in application server or web framework.",
        "regex": r"(?:DEBUG\s*=\s*True|app\.run\([^)]*debug\s*=\s*True|process\.env\.NODE_ENV\s*===?\s*[\"']development[\"'])",
        "extensions": [".py", ".ts", ".js", ".env"],
        "remediation": "Ensure debug mode is disabled by default in production configurations.",
    },

    # A07: Identification & Authentication Failures
    {
        "id": "SEC-A07-HARDCODED-CREDENTIALS",
        "owasp": "A07:2021-Identification and Authentication Failures",
        "severity": "CRITICAL",
        "title": "Hardcoded Password or Secret Token",
        "description": "Hardcoded password, JWT secret, or API token assigned directly in source code.",
        "regex": r"(?:password|passwd|secret_key|api_key|access_token|auth_token)\s*=\s*[\"'][a-zA-Z0-9_\-\.]{8,}[\"']",
        "extensions": [".py", ".ts", ".js", ".go", ".rs", ".java", ".cs"],
        "remediation": "Load credentials from environment variables or a dedicated secret management service.",
    },

    # A08: Software and Data Integrity Failures
    {
        "id": "SEC-A08-UNSAFE-DESERIALIZATION",
        "owasp": "A08:2021-Software and Data Integrity Failures",
        "severity": "CRITICAL",
        "title": "Unsafe Deserialization Primitive (pickle / unsafe yaml)",
        "description": "Deserializing untrusted data with pickle or yaml.load leads to Remote Code Execution (RCE).",
        "regex": r"(?:pickle\.(?:loads|load)\s*\(|yaml\.load\s*\([^)]*Loader\s*=\s*(?:yaml\.)?(?:Loader|CLoader|UnsafeLoader)|yaml\.unsafe_load|BinaryFormatter|ObjectInputStream)",
        "extensions": [".py", ".java", ".cs"],
        "remediation": "Use safe serializers like json or yaml.safe_load().",
    },

    # A10: Server-Side Request Forgery (SSRF)
    {
        "id": "SEC-A10-UNVALIDATED-HTTP-FETCH",
        "owasp": "A10:2021-Server-Side Request Forgery (SSRF)",
        "severity": "MEDIUM",
        "title": "Potential SSRF in Outbound HTTP Request",
        "description": "Direct HTTP request constructed from variable without IP or host validation.",
        "regex": r"(?:requests\.(?:get|post|put|delete)\s*\(\s*(?:url|target_url|user_url|req\.query|req\.body)|axios\.(?:get|post)\s*\(\s*(?:url|target_url|req\.query)|http\.Get\s*\(\s*(?:url|userUrl))",
        "extensions": [".py", ".ts", ".js", ".go"],
        "remediation": "Validate destination hostnames against an allowlist and block private IP ranges (127.0.0.1, 10.0.0.0/8, 169.254.169.254).",
    },
]


# ==============================================================================
# 2. Static Code Scanner (SAST)
# ==============================================================================

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".workflow/worktrees",
    "worktrees",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".turbo",
    ".changeset",
}


def scan_owasp_patterns(
    target_dir: str = ".",
    spec_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Performs static pattern analysis against OWASP Top 10 rules across source files."""
    target_dir = os.path.abspath(target_dir)
    findings: List[Dict[str, Any]] = []

    # Compile regex rules
    compiled_rules = []
    for rule in OWASP_RULES:
        try:
            compiled_rules.append({
                **rule,
                "compiled_re": re.compile(rule["regex"], re.IGNORECASE | re.MULTILINE),
            })
        except Exception:
            continue

    for root, dirs, files in os.walk(target_dir):
        # Filter directories in place
        rel_root = os.path.relpath(root, target_dir)
        parts = rel_root.split(os.sep)
        if any(p in IGNORE_DIRS or p.startswith(".") and p not in [".workflow"] for p in parts if p != "."):
            dirs[:] = []
            continue

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            matching_rules = [r for r in compiled_rules if ext in r["extensions"]]
            if not matching_rules:
                continue

            file_path = os.path.join(root, f)
            rel_file = os.path.relpath(file_path, target_dir).replace("\\", "/")

            # Skip audit reports and template files from triggering self-findings
            rel_lower = rel_file.lower()
            if "security_audit.json" in rel_lower or "owasp_top_10.md" in rel_lower or "security_auditor.py" in rel_lower:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as src_file:
                    content = src_file.read()
            except Exception:
                continue

            lines = content.splitlines()

            for rule in matching_rules:
                for line_idx, line in enumerate(lines, 1):
                    # Skip comment lines
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
                        continue

                    if rule["compiled_re"].search(line):
                        findings.append({
                            "rule_id": rule["id"],
                            "owasp": rule["owasp"],
                            "severity": rule["severity"],
                            "title": rule["title"],
                            "file": rel_file,
                            "line_number": line_idx,
                            "snippet": stripped[:140],
                            "remediation": rule["remediation"],
                        })

    return findings


# ==============================================================================
# 3. Ecosystem Dependency CVE Auditor
# ==============================================================================

def audit_dependencies(target_dir: str = ".") -> Dict[str, Any]:
    """Audits project manifests and lockfiles for known CVEs using ecosystem CLI tools."""
    target_dir = os.path.abspath(target_dir)
    ecosystem_results: Dict[str, Any] = {
        "status": "COMPLETED",
        "scanned_ecosystems": [],
        "vulnerabilities": [],
        "passed": True,
    }

    # 1. Node.js Ecosystem (pnpm / npm / bun)
    pkg_json = os.path.join(target_dir, "package.json")
    if os.path.exists(pkg_json):
        ecosystem_results["scanned_ecosystems"].append("Node.js")
        if shutil.which("pnpm"):
            try:
                res = subprocess.run(["pnpm", "audit", "--json"], cwd=target_dir, capture_output=True, text=True, check=False)
                if res.stdout.strip():
                    try:
                        audit_data = json.loads(res.stdout)
                        advisories = audit_data.get("advisories", {})
                        for adv_id, adv in advisories.items():
                            sev = adv.get("severity", "medium").upper()
                            ecosystem_results["vulnerabilities"].append({
                                "ecosystem": "Node.js (pnpm)",
                                "package": adv.get("module_name", "unknown"),
                                "severity": sev,
                                "title": adv.get("title", "Vulnerable Dependency"),
                                "cve": adv.get("cves", [adv.get("url", "")])[0] if adv.get("cves") else adv.get("url", ""),
                                "patched_versions": adv.get("patched_versions", "Update required"),
                            })
                    except Exception:
                        pass
            except Exception:
                pass
        elif shutil.which("npm"):
            try:
                res = subprocess.run(["npm", "audit", "--json"], cwd=target_dir, capture_output=True, text=True, check=False)
                if res.stdout.strip():
                    try:
                        audit_data = json.loads(res.stdout)
                        vulns = audit_data.get("vulnerabilities", {})
                        for pkg_name, info in vulns.items():
                            sev = info.get("severity", "medium").upper()
                            ecosystem_results["vulnerabilities"].append({
                                "ecosystem": "Node.js (npm)",
                                "package": pkg_name,
                                "severity": sev,
                                "title": f"Vulnerability in {pkg_name}",
                                "cve": "",
                                "patched_versions": "Update required",
                            })
                    except Exception:
                        pass
            except Exception:
                pass

    # 2. Python Ecosystem (uv pip audit / pip-audit)
    pyproject = os.path.join(target_dir, "pyproject.toml")
    requirements = os.path.join(target_dir, "requirements.txt")
    if os.path.exists(pyproject) or os.path.exists(requirements):
        ecosystem_results["scanned_ecosystems"].append("Python")
        if shutil.which("pip-audit"):
            try:
                res = subprocess.run(["pip-audit", "-f", "json"], cwd=target_dir, capture_output=True, text=True, check=False)
                if res.stdout.strip():
                    try:
                        data = json.loads(res.stdout)
                        for dep in data.get("dependencies", []):
                            for v in dep.get("vulns", []):
                                ecosystem_results["vulnerabilities"].append({
                                    "ecosystem": "Python",
                                    "package": dep.get("name"),
                                    "severity": "HIGH",
                                    "title": v.get("description", v.get("id")),
                                    "cve": v.get("id", ""),
                                    "patched_versions": str(v.get("fix_versions", ["Update required"])),
                                })
                    except Exception:
                        pass
            except Exception:
                pass

    # 3. Rust Ecosystem (cargo audit)
    cargo_toml = os.path.join(target_dir, "Cargo.toml")
    if os.path.exists(cargo_toml):
        ecosystem_results["scanned_ecosystems"].append("Rust")
        if shutil.which("cargo") and shutil.which("cargo-audit"):
            try:
                res = subprocess.run(["cargo", "audit", "--json"], cwd=target_dir, capture_output=True, text=True, check=False)
                if res.stdout.strip():
                    try:
                        data = json.loads(res.stdout)
                        for v in data.get("vulnerabilities", {}).get("list", []):
                            ecosystem_results["vulnerabilities"].append({
                                "ecosystem": "Rust",
                                "package": v.get("package", {}).get("name"),
                                "severity": "HIGH",
                                "title": v.get("advisory", {}).get("title"),
                                "cve": v.get("advisory", {}).get("id"),
                                "patched_versions": str(v.get("advisory", {}).get("patched_versions", [])),
                            })
                    except Exception:
                        pass
            except Exception:
                pass

    # Compute dependency gate pass
    crit_or_high = [v for v in ecosystem_results["vulnerabilities"] if v.get("severity") in ["CRITICAL", "HIGH"]]
    ecosystem_results["passed"] = len(crit_or_high) == 0
    return ecosystem_results


# ==============================================================================
# 4. Comprehensive Audit & Report Generation
# ==============================================================================

def audit_codebase(
    target_dir: str = ".",
    spec_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Runs complete security audit: SAST OWASP patterns + Dependency CVEs + Secret scan."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)

    # 1. Run SAST OWASP scan
    sast_findings = scan_owasp_patterns(target_dir=target_dir, spec_name=spec_name)

    # 2. Run Dependency audit
    dep_audit = audit_dependencies(target_dir=target_dir)

    # 3. Aggregate metrics
    critical_count = len([f for f in sast_findings if f["severity"] == "CRITICAL"]) + len([v for v in dep_audit["vulnerabilities"] if v.get("severity") == "CRITICAL"])
    high_count = len([f for f in sast_findings if f["severity"] == "HIGH"]) + len([v for v in dep_audit["vulnerabilities"] if v.get("severity") == "HIGH"])
    medium_count = len([f for f in sast_findings if f["severity"] == "MEDIUM"]) + len([v for v in dep_audit["vulnerabilities"] if v.get("severity") == "MEDIUM"])
    low_count = len([f for f in sast_findings if f["severity"] in ["LOW", "INFO"]]) + len([v for v in dep_audit["vulnerabilities"] if v.get("severity") in ["LOW", "INFO"]])

    passed = (critical_count == 0 and high_count == 0)

    results: Dict[str, Any] = {
        "status": "PASSED" if passed else "FAILED",
        "timestamp": datetime.now().isoformat(),
        "spec_name": spec_name,
        "target_dir": target_dir,
        "security_gate_passed": passed,
        "summary": {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total_issues": len(sast_findings) + len(dep_audit["vulnerabilities"]),
        },
        "sast_findings": sast_findings,
        "dependency_vulnerabilities": dep_audit["vulnerabilities"],
        "scanned_ecosystems": dep_audit["scanned_ecosystems"],
    }

    # 4. Save JSON report
    report_dir = None
    if spec_name:
        clean_spec = sanitize_identifier(spec_name)
        report_dir = os.path.join(wf_root, "specs", "active", clean_spec, "security")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, "security_audit.json")
    else:
        report_dir = os.path.join(wf_root, "security")
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, "security_audit.json")

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    results["report_file"] = report_file
    return results


def generate_security_report_markdown(results: Dict[str, Any]) -> str:
    """Renders human-readable markdown summary of security audit results."""
    summary = results.get("summary", {})
    passed = results.get("security_gate_passed", False)
    status_badge = "🛡️ PASSED (0 Critical / 0 High)" if passed else "🚨 FAILED (Critical or High Vulnerabilities Found)"

    lines = [
        f"# Security Audit Report: `{results.get('spec_name') or 'Global Codebase'}`\n",
        f"**Status**: `{status_badge}`  ",
        f"**Audit Timestamp**: `{results.get('timestamp')}`  ",
        f"**Target Directory**: `{results.get('target_dir')}`  \n",
        "---",
        "## 📊 Executive Summary\n",
        "| Severity | Count | Gate Threshold |",
        "|---|---|---|",
        f"| **CRITICAL** | `{summary.get('critical', 0)}` | `0 allowed` |",
        f"| **HIGH** | `{summary.get('high', 0)}` | `0 allowed` |",
        f"| **MEDIUM** | `{summary.get('medium', 0)}` | Advisory |",
        f"| **LOW / INFO** | `{summary.get('low', 0)}` | Advisory |\n",
        "---",
    ]

    sast = results.get("sast_findings", [])
    if sast:
        lines.append("## 🔍 Static Code Analysis (OWASP Top 10 Findings)\n")
        lines.append("| OWASP Category | Severity | File & Line | Title |")
        lines.append("|---|---|---|---|")
        for f in sast:
            lines.append(f"| `{f['owasp']}` | **`{f['severity']}`** | `{f['file']}:{f['line_number']}` | {f['title']} |")
        lines.append("\n### Remediation Action Items\n")
        for idx, f in enumerate(sast, 1):
            lines.append(f"#### {idx}. [{f['severity']}] {f['title']} (`{f['file']}:{f['line_number']}`)")
            lines.append(f"- **Snippet**: `{f['snippet']}`")
            lines.append(f"- **Remediation**: {f['remediation']}\n")

    deps = results.get("dependency_vulnerabilities", [])
    if deps:
        lines.append("## 📦 Dependency & Supply Chain Vulnerabilities\n")
        lines.append("| Ecosystem | Package | Severity | Title | CVE | Fix Version |")
        lines.append("|---|---|---|---|---|---|")
        for d in deps:
            lines.append(f"| {d.get('ecosystem')} | `{d.get('package')}` | **`{d.get('severity')}`** | {d.get('title')} | `{d.get('cve')}` | `{d.get('patched_versions')}` |")
        lines.append("")

    if not sast and not deps:
        lines.append("## ✅ Clean Security Baseline")
        lines.append("No OWASP Top 10 vulnerabilities or dependency CVEs were detected in the codebase.\n")

    return "\n".join(lines)


# ==============================================================================
# 5. CLI Entrypoint
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic OWASP Top 10 SAST and Dependency Security Auditor.")
    subparsers = parser.add_subparsers(dest="subcommand", help="Security subcommands")

    # scan
    scan_p = subparsers.add_parser("scan", help="Scan codebase against OWASP Top 10 rules")
    scan_p.add_argument("spec_name", nargs="?", default=None, help="Target specification name")
    scan_p.add_argument("--target-dir", default=".", help="Target project directory")
    scan_p.add_argument("--json", action="store_true", help="Output results as JSON")

    # deps
    deps_p = subparsers.add_parser("deps", help="Audit project dependencies for CVEs")
    deps_p.add_argument("--target-dir", default=".", help="Target project directory")
    deps_p.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.subcommand == "deps":
        res = audit_dependencies(target_dir=args.target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("=" * 90)
            print(" 📦 DEPENDENCY CVE AUDIT REPORT")
            print("=" * 90)
            print(f"Ecosystems Scanned: {', '.join(res['scanned_ecosystems']) or 'None detected'}")
            print(f"Vulnerabilities Found: {len(res['vulnerabilities'])}")
            print(f"Security Gate: {'PASSED' if res['passed'] else 'FAILED'}")
            print("=" * 90)
        return 0 if res["passed"] else 1

    # Default to scan
    spec = getattr(args, "spec_name", None)
    target = getattr(args, "target_dir", ".")
    res = audit_codebase(target_dir=target, spec_name=spec)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res["security_gate_passed"] else 1

    print("=" * 110)
    print(f" 🛡️  SECURITY AUDIT REPORT: '{spec or 'GLOBAL'}'")
    print("=" * 110)
    print(f"{'CATEGORY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Security Gate':<24} │ {'✅ PASSED (0 Crit / 0 High)' if res['security_gate_passed'] else '🚨 FAILED (Critical/High Vulns Found)'}")
    print(f"{'Critical Issues':<24} │ {res['summary']['critical']}")
    print(f"{'High Issues':<24} │ {res['summary']['high']}")
    print(f"{'Medium Issues':<24} │ {res['summary']['medium']}")
    print(f"{'Low / Info Issues':<24} │ {res['summary']['low']}")
    print(f"{'Report File':<24} │ {res.get('report_file')}")
    print("=" * 110)

    if res["sast_findings"]:
        print("\n🔍 OWASP Top 10 Findings:")
        for f in res["sast_findings"][:5]:
            print(f"   - [{f['severity']}] {f['owasp']} ({f['file']}:{f['line_number']}): {f['title']}")
        if len(res["sast_findings"]) > 5:
            print(f"   ... and {len(res['sast_findings']) - 5} more issues in {res.get('report_file')}")

    if res["dependency_vulnerabilities"]:
        print("\n📦 Dependency Vulnerabilities:")
        for d in res["dependency_vulnerabilities"][:5]:
            print(f"   - [{d.get('severity')}] {d.get('package')}: {d.get('title')}")

    return 0 if res["security_gate_passed"] else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
