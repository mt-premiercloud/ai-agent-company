"""Autoresearch-inspired improvement loop for agent prompts.

Implements the git ratchet pattern:
1. Agent performs a task
2. Immutable evaluation scores the result
3. If score improved → keep changes, update baseline
4. If score degraded → revert, log failure
5. Repeat

Applied to: agent system prompts and skills improvement.
"""

import os
import json
import subprocess
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'improvement_results.tsv')
BASELINE_FILE = os.path.join(os.path.dirname(__file__), '..', 'improvement_baseline.json')

import logging
log = logging.getLogger('improvement_loop')


def load_baseline() -> dict:
    """Load current baseline scores."""
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    return {"scores": {}, "version": 0}


def save_baseline(baseline: dict):
    """Save updated baseline."""
    with open(BASELINE_FILE, 'w') as f:
        json.dump(baseline, f, indent=2)


def log_result(agent_role: str, metric: str, score: float, status: str, description: str):
    """Append result to TSV log (autoresearch pattern)."""
    timestamp = datetime.utcnow().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp}\t{agent_role}\t{metric}\t{score:.4f}\t{status}\t{description}\n")
    log.info("Result logged: %s %s=%.4f %s", agent_role, metric, score, status)


def evaluate_agent_response(role: str, task: str, response: str) -> dict:
    """Immutable evaluation of agent response quality.

    Scores on multiple dimensions (0-1):
    - relevance: Does the response address the task?
    - completeness: Are all aspects covered?
    - gcp_compliance: Does it stick to GCP-only?
    - actionability: Can someone act on this immediately?
    - depth: Is the analysis deep or surface-level?

    Uses a separate Gemini call with immutable evaluation prompt.
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'vendor', 'hermes-agent'))

    import google.auth
    import google.auth.transport.requests
    from openai import OpenAI

    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)

    client = OpenAI(
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=creds.token,
    )

    eval_prompt = f"""You are an IMMUTABLE evaluation function. Score this agent response.

TASK: {task}
AGENT ROLE: {role}
RESPONSE: {response[:3000]}

Score each dimension from 0.0 to 1.0:
- relevance: Does the response address the specific task?
- completeness: Are all aspects of the task covered?
- gcp_compliance: Does it use only GCP services (no AWS/Azure/Vercel)?
- actionability: Can someone immediately act on the output?
- depth: Is the analysis deep with specific details, or surface-level generic?

Output ONLY valid JSON:
{{"relevance": 0.0, "completeness": 0.0, "gcp_compliance": 0.0, "actionability": 0.0, "depth": 0.0, "overall": 0.0, "notes": ""}}
"""

    resp = client.chat.completions.create(
        model="google/gemini-3.1-pro-preview",
        messages=[{"role": "user", "content": eval_prompt}],
        max_tokens=1000,
        temperature=0.1,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        scores = json.loads(text)
        scores["overall"] = sum(scores.get(k, 0) for k in ["relevance", "completeness", "gcp_compliance", "actionability", "depth"]) / 5
        return scores
    except (json.JSONDecodeError, IndexError):
        return {"overall": 0.5, "error": "Could not parse evaluation", "raw": text[:200]}


def ratchet_check(role: str, task: str, response: str) -> dict:
    """Run the autoresearch ratchet: evaluate and compare to baseline.

    Returns dict with:
    - improved: bool
    - scores: current scores
    - baseline_score: previous overall score
    - delta: improvement amount
    """
    baseline = load_baseline()
    scores = evaluate_agent_response(role, task, response)
    current_overall = scores.get("overall", 0)

    baseline_key = f"{role}_overall"
    baseline_score = baseline["scores"].get(baseline_key, 0)

    improved = current_overall > baseline_score
    delta = current_overall - baseline_score

    if improved:
        baseline["scores"][baseline_key] = current_overall
        baseline["version"] += 1
        save_baseline(baseline)
        log_result(role, "overall", current_overall, "PASS", f"Improved by {delta:.4f}")
    else:
        log_result(role, "overall", current_overall, "FAIL", f"Degraded by {abs(delta):.4f}")

    return {
        "improved": improved,
        "scores": scores,
        "baseline_score": baseline_score,
        "delta": delta,
    }


if __name__ == "__main__":
    # Quick test of the evaluation
    test_result = evaluate_agent_response(
        "ceo",
        "Assess a task management SaaS for freelancers",
        "This project needs careful planning. We should use Cloud Run for hosting, Cloud SQL for database, and Firebase Auth for authentication. The market is competitive with Asana and Trello, but there's a niche for freelancer-specific features like invoicing integration and time tracking.",
    )
    print("Evaluation:", json.dumps(test_result, indent=2))
