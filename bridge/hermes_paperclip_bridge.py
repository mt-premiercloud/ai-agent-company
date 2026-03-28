"""Bridge between Paperclip (Company OS) and Hermes (Agent Brain).

This server receives heartbeats from Paperclip and routes them
to the appropriate Hermes agent instance. Each agent gets:
- Fresh Vertex AI token
- Task context from Paperclip
- Hermes tools (web search, code execution, delegation)
- Persistent memory across invocations

Runs as HTTP server that Paperclip calls via its HTTP adapter.
"""

import os
import sys
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Add hermes to path
HERMES_PATH = os.path.join(os.path.dirname(__file__), '..', 'vendor', 'hermes-agent')
sys.path.insert(0, os.path.abspath(HERMES_PATH))

logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)-8s %(name)-20s | %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('bridge')

# Agent configurations — maps Paperclip agent roles to Hermes system prompts
AGENT_CONFIGS = {
    "ceo": {
        "system_prompt": """You are the CEO Agent of an AI Development Agency.
Your job: receive project ideas, challenge assumptions, create project blueprints.
Use the deep-problem-analysis skill for every new project.
Always push back on vague ideas. Be a senior consultant, not a yes-man.
Coordinate all other agents through Paperclip's task system.
GCP-ONLY: All infrastructure must use Google Cloud Platform.""",
        "max_iterations": 15,
        "tools": ["web_search", "delegation", "file"],
    },
    "researcher": {
        "system_prompt": """You are a Research Agent at an AI Development Agency.
Your specialties: market research, technology evaluation, deep problem analysis.
Always search the web with Google Search grounding for real data.
Cross-reference findings from multiple sources. Minimum 10 searches per research task.
GCP-ONLY: All technology recommendations must use GCP services.""",
        "max_iterations": 20,
        "tools": ["web_search", "file", "code_execution"],
    },
    "cto": {
        "system_prompt": """You are the Architect Agent (CTO) of an AI Development Agency.
You make final technology decisions and produce Architecture Decision Records.
Include: Mermaid diagrams, prerequisites checklist, risk analysis.
GCP-ONLY: All architecture must use Google Cloud Platform services.
Never recommend AWS, Azure, Vercel, Supabase or non-GCP services.""",
        "max_iterations": 10,
        "tools": ["web_search", "file"],
    },
    "pm": {
        "system_prompt": """You are the Project Planner at an AI Development Agency.
Break projects into small, actionable tasks (2-5 minutes each for AI agents).
Every task must have Given/When/Then acceptance criteria.
Link dependencies explicitly. Label each task for the correct builder agent.
GCP-ONLY: All infrastructure tasks must target GCP.""",
        "max_iterations": 15,
        "tools": ["file"],
    },
    "engineer": {
        "system_prompt": """You are a Builder Agent (Software Engineer) at an AI Development Agency.
Follow the Superpowers workflow: Brainstorm → Plan → TDD → Build → Review → Ship.
NO code before design approval. NO completion claims without test evidence.
Use git worktrees for isolation. Write comprehensive tests.
GCP-ONLY: All infrastructure must use Google Cloud Platform.""",
        "max_iterations": 30,
        "tools": ["file", "code_execution", "terminal"],
    },
    "qa": {
        "system_prompt": """You are the QA Agent at an AI Development Agency.
Test using real browser interactions (Playwright/Chromium).
Auto-fix bugs with atomic commits per fix.
Generate regression tests for each fix. Verify before claiming done.
Report: before/after health scores, bugs found, bugs fixed.""",
        "max_iterations": 20,
        "tools": ["file", "code_execution", "terminal", "browser"],
    },
    "devops": {
        "system_prompt": """You are the Security Agent at an AI Development Agency.
Run OWASP Top 10 + STRIDE threat model audits.
Check: SQL injection, XSS, CSRF, auth bypass, trust boundaries.
Flag issues with severity and remediation steps.
GCP-ONLY: All security recommendations for GCP services.""",
        "max_iterations": 15,
        "tools": ["file", "code_execution", "web_search"],
    },
}


def get_vertex_token():
    """Get fresh Vertex AI access token."""
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def run_hermes_agent(role: str, task_description: str, context: str = "") -> str:
    """Run a Hermes agent with the given role and task.

    Args:
        role: Agent role (ceo, researcher, cto, pm, engineer, qa, devops)
        task_description: The task to perform
        context: Additional context (from Paperclip ticket)

    Returns:
        Agent's response text
    """
    config = AGENT_CONFIGS.get(role, AGENT_CONFIGS["researcher"])
    token = get_vertex_token()

    log.info("Running Hermes agent: role=%s task=%s...", role, task_description[:80])
    log.debug("System prompt: %s...", config["system_prompt"][:100])

    from run_agent import AIAgent

    agent = AIAgent(
        model="google/gemini-3.1-pro-preview",
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=token,
        ephemeral_system_prompt=config["system_prompt"],
        max_iterations=config["max_iterations"],
        quiet_mode=True,
        skip_memory=False,
        skip_context_files=True,
    )

    user_message = task_description
    if context:
        user_message = f"## Task\n{task_description}\n\n## Context\n{context}"

    result = agent.chat(user_message)
    log.info("Agent completed: %d chars response", len(result) if result else 0)
    return result or "Agent returned no response."


class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP handler for Paperclip heartbeat requests."""

    def do_POST(self):
        """Handle heartbeat from Paperclip."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        log.info("Heartbeat received: %s", json.dumps(data, indent=2)[:500])

        role = data.get("role", "researcher")
        task = data.get("task", data.get("description", "No task specified"))
        context = data.get("context", "")

        try:
            result = run_hermes_agent(role, task, context)
            response = {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            log.error("Agent failed: %s", e)
            response = {"status": "error", "error": str(e), "timestamp": datetime.utcnow().isoformat()}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_GET(self):
        """Health check."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "agents": list(AGENT_CONFIGS.keys())}).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        log.debug(format, *args)


def main():
    port = int(os.environ.get('BRIDGE_PORT', 8200))
    server = HTTPServer(('127.0.0.1', port), BridgeHandler)
    log.info("=" * 60)
    log.info("Hermes-Paperclip Bridge running on http://127.0.0.1:%d", port)
    log.info("Agents: %s", ', '.join(AGENT_CONFIGS.keys()))
    log.info("Model: gemini-3.1-pro-preview via Vertex AI (global)")
    log.info("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Bridge shutting down.")
        server.server_close()


if __name__ == '__main__':
    main()
