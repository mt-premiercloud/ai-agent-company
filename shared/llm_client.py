"""Vertex AI LLM wrapper — all agents call Gemini through this."""

from google import genai
from google.genai import types
from shared.config import GCP_PROJECT_ID, GCP_LOCATION, VERTEX_AI_MODEL, get_logger

log = get_logger("shared.llm_client")

_client = None


def _get_client() -> genai.Client:
    """Singleton Vertex AI client."""
    global _client
    if _client is None:
        log.debug("Initializing Vertex AI client: project=%s location=%s", GCP_PROJECT_ID, GCP_LOCATION)
        _client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    return _client


def call_llm(
    system_prompt: str,
    user_message: str,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """Single LLM call — fresh context every time (core principle).

    Args:
        system_prompt: The agent's system instructions.
        user_message: The task/data for this invocation.
        model: Override model (defaults to VERTEX_AI_MODEL from .env).
        temperature: Creativity level.
        max_tokens: Max response length.

    Returns:
        The LLM's text response.
    """
    model = model or VERTEX_AI_MODEL
    client = _get_client()

    log.info("LLM call: model=%s temp=%.1f max_tokens=%d", model, temperature, max_tokens)
    log.debug("System prompt (%d chars): %s...", len(system_prompt), system_prompt[:200])
    log.debug("User message (%d chars): %s...", len(user_message), user_message[:200])

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(role="user", parts=[types.Part(text=user_message)]),
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )

    result = response.text
    log.info("LLM response received: %d chars", len(result))
    log.debug("Response preview: %s...", result[:300])
    return result
