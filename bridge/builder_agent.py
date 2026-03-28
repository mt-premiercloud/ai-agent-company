"""Builder Agent — Actually writes code, creates files, runs tests.

Takes a build task from Paperclip, calls Gemini to generate code,
writes files to the workspace, runs tests, and commits to git.
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

log = logging.getLogger("builder_agent")

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workspace'))


def get_vertex_token():
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def call_gemini(system_prompt: str, user_message: str, max_tokens: int = 8192) -> str:
    """Direct Gemini API call for code generation."""
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
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content


def run_command(cmd: str, cwd: str = None, timeout: int = 60) -> dict:
    """Run a shell command and return output."""
    log.debug("Running: %s (in %s)", cmd, cwd or ".")
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or WORKSPACE,
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1, "success": False}


def init_project(project_name: str) -> str:
    """Initialize a new project in the workspace."""
    project_dir = os.path.join(WORKSPACE, project_name)
    os.makedirs(project_dir, exist_ok=True)

    # Init git
    run_command("git init", cwd=project_dir)
    run_command('git config user.email "builder@ai-agency.dev"', cwd=project_dir)
    run_command('git config user.name "Builder Agent"', cwd=project_dir)

    log.info("Project initialized: %s", project_dir)
    return project_dir


def write_file(project_dir: str, filepath: str, content: str):
    """Write a file to the project directory."""
    full_path = os.path.join(project_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    log.info("Wrote: %s (%d chars)", filepath, len(content))


def commit(project_dir: str, message: str):
    """Git add and commit."""
    run_command("git add -A", cwd=project_dir)
    run_command(f'git commit -m "{message}"', cwd=project_dir)
    log.info("Committed: %s", message)


def build_task(task_title: str, task_description: str, project_name: str = None, context: str = "") -> dict:
    """Execute a build task — generate code, write files, run tests.

    Args:
        task_title: What to build
        task_description: Detailed description with acceptance criteria
        project_name: Name for the project directory
        context: Architecture/planning context from previous agents

    Returns:
        dict with files_created, tests_passed, commit_hash
    """
    log.info("=" * 60)
    log.info("BUILDER AGENT: %s", task_title)
    log.info("=" * 60)

    # Step 1: Init project
    if not project_name:
        project_name = task_title.lower().replace(" ", "-")[:30]
    project_dir = init_project(project_name)

    # Step 2: Ask Gemini to generate the implementation plan with actual code
    system_prompt = """You are a senior software engineer building a project.
You MUST output a JSON array of files to create. Each file has a path and content.
Use ONLY Google Cloud Platform services (Cloud Run, Cloud SQL, Firebase Auth, GCS, Vertex AI).

Output format (JSON only, no markdown):
{
    "files": [
        {"path": "relative/path/to/file.py", "content": "actual file content here"},
        {"path": "tests/test_file.py", "content": "actual test content here"},
        {"path": "requirements.txt", "content": "package list"},
        {"path": "README.md", "content": "project description"}
    ],
    "test_command": "python -m pytest tests/ -v",
    "summary": "What was built"
}

RULES:
- Every feature MUST have a corresponding test file
- Use Python unless the task requires JavaScript/TypeScript
- Include requirements.txt or package.json
- Include a README.md
- All code must be production-ready, not scaffolds
- GCP ONLY: never reference AWS, Azure, Vercel, Supabase
"""

    user_msg = f"""## Task: {task_title}

## Description
{task_description}

## Architecture Context
{context[:3000]}

Generate the complete implementation as a JSON array of files.
"""

    log.info("Step 1: Generating code with Gemini 3.1 Pro...")
    raw_response = call_gemini(system_prompt, user_msg, max_tokens=8192)

    # Step 3: Parse the files
    log.info("Step 2: Parsing generated files...")
    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
        plan = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to repair
        log.warning("JSON parse failed, attempting repair...")
        try:
            # Find the JSON object
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start >= 0 and end > start:
                plan = json.loads(raw_response[start:end])
            else:
                plan = {"files": [], "summary": "Parse failed", "raw": raw_response[:500]}
        except:
            plan = {"files": [], "summary": "Parse failed", "raw": raw_response[:500]}

    files = plan.get("files", [])
    test_cmd = plan.get("test_command", "echo 'no tests configured'")
    summary = plan.get("summary", "Build complete")

    # Step 4: Write all files
    log.info("Step 3: Writing %d files...", len(files))
    files_created = []
    for f in files:
        path = f.get("path", "")
        content = f.get("content", "")
        if path and content:
            write_file(project_dir, path, content)
            files_created.append(path)

    # Step 5: Install dependencies
    log.info("Step 4: Installing dependencies...")
    if os.path.exists(os.path.join(project_dir, "requirements.txt")):
        dep_result = run_command("pip install -r requirements.txt --quiet", cwd=project_dir, timeout=120)
        log.debug("Deps: %s", "OK" if dep_result["success"] else dep_result["stderr"][:200])

    # Step 6: Run tests
    log.info("Step 5: Running tests: %s", test_cmd)
    test_result = run_command(test_cmd, cwd=project_dir, timeout=120)
    tests_passed = test_result["success"]
    log.info("Tests: %s", "PASSED" if tests_passed else "FAILED")
    if not tests_passed:
        log.debug("Test output: %s", test_result["stdout"][:500])
        log.debug("Test errors: %s", test_result["stderr"][:500])

    # Step 7: Commit
    log.info("Step 6: Committing...")
    commit(project_dir, f"feat: {task_title}")

    # Get commit hash
    hash_result = run_command("git rev-parse --short HEAD", cwd=project_dir)
    commit_hash = hash_result["stdout"].strip()

    result = {
        "project_dir": project_dir,
        "files_created": files_created,
        "test_command": test_cmd,
        "tests_passed": tests_passed,
        "test_output": test_result["stdout"][:1000],
        "test_errors": test_result["stderr"][:500] if not tests_passed else "",
        "commit_hash": commit_hash,
        "summary": summary,
    }

    log.info("=" * 60)
    log.info("BUILDER COMPLETE: %d files, tests=%s, commit=%s",
             len(files_created), "PASS" if tests_passed else "FAIL", commit_hash)
    log.info("=" * 60)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)-8s %(name)-20s | %(message)s', datefmt='%H:%M:%S')
    result = build_task(
        "Create a basic Flask API with health endpoint",
        "Create a simple Flask API server with a /health endpoint that returns {status: ok}. Include a test.",
        project_name="test-api",
    )
    print(json.dumps(result, indent=2))
