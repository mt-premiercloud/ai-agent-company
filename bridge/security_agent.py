"""Security Agent — OWASP Top 10 + STRIDE threat model audit.

Scans actual code files for vulnerabilities, checks dependencies,
and produces a security report with severity ratings.
"""

import os
import sys
import json
import subprocess
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

log = logging.getLogger("security_agent")


def get_vertex_token():
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def call_gemini(system_prompt: str, user_message: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=get_vertex_token(),
    )
    resp = client.chat.completions.create(
        model="google/gemini-3.1-pro-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        max_tokens=6000,
        temperature=0.1,
    )
    return resp.choices[0].message.content


def run_command(cmd: str, cwd: str = None, timeout: int = 60) -> dict:
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "success": result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1, "success": False}


# OWASP Top 10 patterns to scan for
VULN_PATTERNS = {
    "SQL Injection": [
        r"f\".*SELECT.*{",
        r"f\".*INSERT.*{",
        r"f\".*UPDATE.*{",
        r"f\".*DELETE.*{",
        r"\.format\(.*\).*SELECT",
        r"execute\(.*\+.*\)",
        r"execute\(f\"",
    ],
    "XSS": [
        r"innerHTML\s*=",
        r"\.html\(",
        r"document\.write\(",
        r"render_template_string\(",
        r"\|safe",
    ],
    "Hardcoded Secrets": [
        r"password\s*=\s*['\"]",
        r"api_key\s*=\s*['\"]",
        r"secret\s*=\s*['\"]",
        r"token\s*=\s*['\"]",
        r"private_key\s*=\s*['\"]",
        r"AWS_SECRET",
        r"AZURE_KEY",
    ],
    "Insecure Deserialization": [
        r"pickle\.loads",
        r"yaml\.load\(",
        r"eval\(",
        r"exec\(",
    ],
    "Missing Auth": [
        r"@app\.route.*\n(?!.*@login_required)",
        r"@app\.route.*\n(?!.*@auth)",
    ],
    "CORS Misconfiguration": [
        r"Access-Control-Allow-Origin.*\*",
        r"CORS\(.*origins=\[?\"\*",
    ],
    "Path Traversal": [
        r"open\(.*\+.*\)",
        r"os\.path\.join\(.*request",
    ],
}


def scan_code_patterns(project_dir: str) -> list:
    """Scan code for known vulnerability patterns."""
    import re
    findings = []

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'venv', '.venv')]
        for fname in files:
            if not fname.endswith(('.py', '.js', '.ts', '.html', '.jsx', '.tsx')):
                continue
            filepath = os.path.join(root, fname)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
            except:
                continue

            rel_path = os.path.relpath(filepath, project_dir)

            for vuln_type, patterns in VULN_PATTERNS.items():
                for pattern in patterns:
                    for i, line in enumerate(lines):
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append({
                                "type": vuln_type,
                                "severity": "high" if vuln_type in ("SQL Injection", "Hardcoded Secrets", "Insecure Deserialization") else "medium",
                                "file": rel_path,
                                "line": i + 1,
                                "evidence": line.strip()[:100],
                                "pattern": pattern,
                            })
    return findings


def check_dependencies(project_dir: str) -> list:
    """Check for known vulnerable dependencies."""
    findings = []

    # Python: pip audit
    if os.path.exists(os.path.join(project_dir, "requirements.txt")):
        result = run_command("pip audit --format json 2>&1", cwd=project_dir, timeout=60)
        if result["stdout"]:
            try:
                audit = json.loads(result["stdout"])
                for vuln in audit.get("vulnerabilities", []):
                    findings.append({
                        "type": "Vulnerable Dependency",
                        "severity": "high",
                        "file": "requirements.txt",
                        "description": f"{vuln.get('name')}: {vuln.get('advisory', '')}",
                    })
            except:
                pass

    # Node.js: npm audit
    if os.path.exists(os.path.join(project_dir, "package.json")):
        result = run_command("npm audit --json 2>&1", cwd=project_dir, timeout=60)
        if result["stdout"]:
            try:
                audit = json.loads(result["stdout"])
                for adv_id, adv in audit.get("advisories", {}).items():
                    findings.append({
                        "type": "Vulnerable Dependency",
                        "severity": adv.get("severity", "medium"),
                        "file": "package.json",
                        "description": f"{adv.get('module_name')}: {adv.get('title', '')}",
                    })
            except:
                pass

    return findings


def run_security_audit(project_dir: str, app_description: str = "") -> dict:
    """Run full security audit on a project.

    1. Pattern-based vulnerability scanning (OWASP Top 10)
    2. Dependency audit (pip audit / npm audit)
    3. AI-powered STRIDE threat model
    4. GCP-specific security checks

    Returns:
        dict with vulnerabilities, threat model, and recommendations
    """
    log.info("=" * 60)
    log.info("SECURITY AGENT: Auditing %s", project_dir)
    log.info("=" * 60)

    results = {
        "project_dir": project_dir,
        "vulnerabilities": [],
        "threat_model": None,
        "recommendations": [],
        "score": 0,
    }

    # Step 1: Pattern scanning
    log.info("Step 1: Scanning for OWASP Top 10 patterns...")
    pattern_vulns = scan_code_patterns(project_dir)
    results["vulnerabilities"].extend(pattern_vulns)
    log.info("Pattern scan found %d potential issues", len(pattern_vulns))

    # Step 2: Dependency audit
    log.info("Step 2: Auditing dependencies...")
    dep_vulns = check_dependencies(project_dir)
    results["vulnerabilities"].extend(dep_vulns)
    log.info("Dependency audit found %d issues", len(dep_vulns))

    # Step 3: AI-powered STRIDE threat model
    log.info("Step 3: Generating STRIDE threat model...")
    project_code = ""
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'venv')]
        for f in files:
            if f.endswith(('.py', '.js', '.ts', '.yaml', '.json', '.env.example')):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    rel = os.path.relpath(filepath, project_dir)
                    project_code += f"\n### {rel}\n```\n{content[:2000]}\n```\n"
                except:
                    pass

    if project_code:
        stride = call_gemini(
            """You are a security officer performing a STRIDE threat model analysis.
Analyze the code and produce a security report.

STRIDE categories:
- Spoofing: Can identities be faked?
- Tampering: Can data be modified?
- Repudiation: Can actions be denied?
- Information Disclosure: Can data leak?
- Denial of Service: Can the system be overwhelmed?
- Elevation of Privilege: Can users gain unauthorized access?

Also check GCP-specific security:
- Are Secret Manager used for credentials?
- Is Cloud SQL using private IP?
- Are Cloud Run services properly authenticated?
- Is HTTPS enforced?

Output JSON only:
{
    "stride": {
        "spoofing": {"risk": "low|medium|high", "details": "...", "mitigation": "..."},
        "tampering": {"risk": "low|medium|high", "details": "...", "mitigation": "..."},
        "repudiation": {"risk": "low|medium|high", "details": "...", "mitigation": "..."},
        "information_disclosure": {"risk": "low|medium|high", "details": "...", "mitigation": "..."},
        "denial_of_service": {"risk": "low|medium|high", "details": "...", "mitigation": "..."},
        "elevation_of_privilege": {"risk": "low|medium|high", "details": "...", "mitigation": "..."}
    },
    "gcp_security": [{"check": "...", "status": "pass|fail", "detail": "..."}],
    "critical_findings": ["..."],
    "recommendations": ["..."],
    "overall_score": 0
}""",
            f"## App Description\n{app_description}\n\n## Code\n{project_code[:8000]}",
        )

        try:
            cleaned = stride.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            threat_model = json.loads(cleaned)
            results["threat_model"] = threat_model
            results["recommendations"] = threat_model.get("recommendations", [])
            results["score"] = threat_model.get("overall_score", 50)
            log.info("STRIDE analysis complete. Score: %d/100", results["score"])
        except:
            log.warning("Could not parse STRIDE output")
            results["threat_model"] = {"raw": stride[:1000]}

    # Summary
    high_count = sum(1 for v in results["vulnerabilities"] if v.get("severity") == "high")
    med_count = sum(1 for v in results["vulnerabilities"] if v.get("severity") == "medium")
    low_count = sum(1 for v in results["vulnerabilities"] if v.get("severity") == "low")

    results["summary"] = {
        "total_vulnerabilities": len(results["vulnerabilities"]),
        "high": high_count,
        "medium": med_count,
        "low": low_count,
        "score": results["score"],
    }

    log.info("=" * 60)
    log.info("SECURITY AUDIT COMPLETE: %d high, %d medium, %d low", high_count, med_count, low_count)
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)-8s %(name)-20s | %(message)s', datefmt='%H:%M:%S')
    if len(sys.argv) > 1:
        result = run_security_audit(sys.argv[1], "A web application")
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python security_agent.py <project_dir>")
