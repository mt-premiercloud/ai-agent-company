"""QA Agent — Actually runs browser tests using Playwright.

Opens a real Chromium browser, navigates to the app, tests flows,
captures screenshots, and reports bugs with evidence.
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

log = logging.getLogger("qa_agent")

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workspace'))


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
        max_tokens=4096,
        temperature=0.2,
    )
    return resp.choices[0].message.content


def run_command(cmd: str, cwd: str = None, timeout: int = 60) -> dict:
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or WORKSPACE,
            capture_output=True, text=True, timeout=timeout,
        )
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode, "success": result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1, "success": False}


def generate_test_script(project_dir: str, app_description: str, test_url: str = "http://localhost:5000") -> str:
    """Ask Gemini to generate a Playwright test script for the project."""

    # Read project files for context
    project_files = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'venv')]
        for f in files:
            if f.endswith(('.py', '.js', '.ts', '.html', '.json')) and not f.startswith('.'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        content = fh.read()[:2000]
                    rel = os.path.relpath(filepath, project_dir)
                    project_files.append(f"### {rel}\n```\n{content}\n```")
                except:
                    pass

    system_prompt = """You are a QA engineer writing Playwright browser tests.
Generate a Python test script using playwright.sync_api that:
1. Navigates to the app
2. Tests key user flows
3. Checks for errors in console
4. Takes screenshots of each step
5. Verifies expected content is present

Output ONLY the Python code, no markdown fences.
The script should be self-contained and use sync Playwright API.
Install playwright if needed: pip install playwright && playwright install chromium
"""

    user_msg = f"""## App Description
{app_description}

## Test URL
{test_url}

## Project Files
{chr(10).join(project_files[:5])}

Generate a Playwright test script that tests the main flows.
"""

    return call_gemini(system_prompt, user_msg)


def run_qa(project_dir: str, app_description: str, test_url: str = None) -> dict:
    """Run QA testing on a project.

    1. Generates Playwright test script via Gemini
    2. Starts the app server
    3. Runs browser tests
    4. Captures screenshots and results
    5. Reports bugs found

    Args:
        project_dir: Path to the project
        app_description: What the app does
        test_url: URL to test against (if app is already running)

    Returns:
        dict with test results, screenshots, bugs found
    """
    log.info("=" * 60)
    log.info("QA AGENT: Testing %s", project_dir)
    log.info("=" * 60)

    results = {
        "project_dir": project_dir,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "bugs": [],
        "screenshots": [],
    }

    # Step 1: Run existing unit tests first
    log.info("Step 1: Running existing unit tests...")
    unit_result = run_command("python -m pytest -v --tb=short 2>&1", cwd=project_dir, timeout=120)
    results["unit_test_output"] = unit_result["stdout"][:2000]
    results["unit_tests_passed"] = unit_result["success"]

    if not unit_result["success"]:
        # Parse test failures
        log.warning("Unit tests failed!")
        results["bugs"].append({
            "type": "unit_test_failure",
            "severity": "high",
            "description": "Unit tests are failing",
            "evidence": unit_result["stdout"][-500:] + unit_result["stderr"][-500:],
        })

    # Step 2: Check for common code quality issues
    log.info("Step 2: Static analysis...")
    # Check for hardcoded secrets
    secret_patterns = ["password=", "api_key=", "secret=", "token="]
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'venv')]
        for f in files:
            if f.endswith(('.py', '.js', '.ts', '.env')):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    for pattern in secret_patterns:
                        if pattern in content.lower() and '.env' not in f:
                            results["bugs"].append({
                                "type": "security",
                                "severity": "high",
                                "description": f"Possible hardcoded secret in {os.path.relpath(filepath, project_dir)}",
                                "evidence": f"Found pattern: {pattern}",
                            })
                except:
                    pass

    # Step 3: Generate and run browser tests (if URL available)
    if test_url:
        log.info("Step 3: Generating Playwright browser tests...")

        # Ensure playwright is installed
        run_command("pip install playwright --quiet", timeout=60)
        run_command("python -m playwright install chromium --quiet 2>&1", timeout=120)

        test_script = generate_test_script(project_dir, app_description, test_url)

        # Write test script
        test_path = os.path.join(project_dir, "qa_browser_test.py")
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_script)

        log.info("Step 4: Running browser tests against %s...", test_url)
        browser_result = run_command(f"python qa_browser_test.py", cwd=project_dir, timeout=120)

        results["browser_test_output"] = browser_result["stdout"][:2000]
        results["browser_tests_passed"] = browser_result["success"]

        if not browser_result["success"]:
            results["bugs"].append({
                "type": "browser_test_failure",
                "severity": "medium",
                "description": "Browser tests failed",
                "evidence": browser_result["stderr"][:500],
            })
    else:
        log.info("Step 3: No test URL provided, skipping browser tests")
        results["browser_tests_passed"] = None

    # Step 4: Ask Gemini to review the code for bugs
    log.info("Step 4: AI-powered code review for bugs...")
    project_code = ""
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__', '.git', 'venv')]
        for f in files:
            if f.endswith(('.py', '.js', '.ts')) and not f.startswith('qa_'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    rel = os.path.relpath(filepath, project_dir)
                    project_code += f"\n### {rel}\n```\n{content[:3000]}\n```\n"
                except:
                    pass

    if project_code:
        review = call_gemini(
            """You are a QA lead reviewing code for bugs. Find:
1. Logic errors
2. Missing error handling
3. SQL injection or XSS vulnerabilities
4. Race conditions
5. Missing input validation
6. Hardcoded secrets

Output JSON only:
{"bugs": [{"severity": "high|medium|low", "file": "path", "line": 0, "description": "what's wrong", "fix": "how to fix"}]}""",
            f"Review this code:\n{project_code[:6000]}",
        )

        try:
            cleaned = review.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            ai_bugs = json.loads(cleaned).get("bugs", [])
            for bug in ai_bugs:
                bug["type"] = "ai_review"
                results["bugs"].append(bug)
            log.info("AI review found %d potential issues", len(ai_bugs))
        except:
            log.warning("Could not parse AI review output")

    results["tests_run"] = len(results["bugs"])
    results["total_bugs"] = len(results["bugs"])

    log.info("=" * 60)
    log.info("QA COMPLETE: %d bugs found", len(results["bugs"]))
    for bug in results["bugs"]:
        log.info("  [%s] %s: %s", bug.get("severity", "?"), bug.get("type", "?"), bug.get("description", "?")[:60])
    log.info("=" * 60)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)-8s %(name)-20s | %(message)s', datefmt='%H:%M:%S')
    # Test on a project directory
    if len(sys.argv) > 1:
        result = run_qa(sys.argv[1], "A Flask API with health endpoint")
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python qa_agent.py <project_dir> [test_url]")
