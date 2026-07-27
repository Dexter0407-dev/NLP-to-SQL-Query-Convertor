"""
Module 2 — Natural Language to SQL Generation
Constructs a prompt with the DB schema and user question,
calls the configured LLM, and extracts a clean SQL string.
"""
from __future__ import annotations

import logging
import re

from app.config import settings
from app.models import SchemaResponse
from app.schema import schema_as_prompt_text

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert SQL assistant. Given a database schema and a user question, generate ONLY the SQL query that answers it.

Rules:
- Output ONLY the raw SQL query — no markdown, no backticks, no explanations.
- Use only the table names and column names that exist in the schema provided.
- If the question cannot be answered from the schema, reply with exactly: UNABLE_TO_ANSWER
- Prefer simple, readable queries.
- Do not add comments.
"""


def _build_user_prompt(question: str, schema: SchemaResponse) -> str:
    schema_text = schema_as_prompt_text(schema)
    return f"""Schema:
{schema_text}

Question: {question}

SQL:"""


def _clean_sql(raw: str) -> str | None:
    """Strip markdown fences and whitespace from the LLM output."""
    text = raw.strip()
    # Remove ```sql ... ``` or ``` ... ```
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    if not text or text == "UNABLE_TO_ANSWER":
        return None

    # Basic sanity: must contain at least one SQL keyword
    if not re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|WITH)\b", text, re.IGNORECASE):
        return None

    return text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    model = settings.llm_model or "gpt-4o-mini"
    client = OpenAI(api_key=settings.llm_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


def _call_groq(prompt: str) -> str:
    from groq import Groq
    model = settings.llm_model or "llama-3.3-70b-versatile"
    client = Groq(api_key=settings.llm_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
        stop=None,
    )
    return resp.choices[0].message.content or ""


def _call_together(prompt: str) -> str:
    """Together AI — OpenAI-compatible, free $1 credit, no card needed."""
    from openai import OpenAI
    model = settings.llm_model or "meta-llama/Llama-3-70b-chat-hf"
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url="https://api.together.xyz/v1",
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


def _call_mistral(prompt: str) -> str:
    """Mistral AI — free tier, OpenAI-compatible endpoint."""
    from openai import OpenAI
    model = settings.llm_model or "mistral-small-latest"
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url="https://api.mistral.ai/v1",
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


def _call_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
    model = settings.llm_model or "claude-3-haiku-20240307"
    client = anthropic.Anthropic(api_key=settings.llm_api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text or ""


def _call_gemini(prompt: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
    model_name = settings.llm_model or "gemini-1.5-flash"
    genai.configure(api_key=settings.llm_api_key)
    model = genai.GenerativeModel(model_name=model_name)
    # Prepend system instructions into the user prompt for older SDK versions
    full_prompt = f"{_SYSTEM_PROMPT}\n\n{prompt}"
    resp = model.generate_content(full_prompt)
    return resp.text or ""


def generate_sql(question: str, schema: SchemaResponse) -> str:
    """
    Generate a SQL query from a natural language question.
    Raises ValueError if the LLM cannot answer or the response cannot be parsed.
    """
    if not settings.llm_api_key:
        raise ValueError(
            "LLM_API_KEY is not configured. "
            "Set it in your environment variables."
        )

    prompt = _build_user_prompt(question, schema)
    provider = settings.llm_provider.lower()

    logger.info("Calling LLM provider '%s' for question: %s", provider, question)

    try:
        if provider == "openai":
            raw = _call_openai(prompt)
        elif provider == "groq":
            raw = _call_groq(prompt)
        elif provider == "together":
            raw = _call_together(prompt)
        elif provider == "mistral":
            raw = _call_mistral(prompt)
        elif provider == "claude":
            raw = _call_claude(prompt)
        elif provider == "gemini":
            raw = _call_gemini(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider!r}. "
                             "Choose openai, groq, together, mistral, claude, or gemini.")
    except Exception as exc:
        logger.exception("LLM call failed")
        raise RuntimeError(f"LLM call failed: {exc}") from exc

    sql = _clean_sql(raw)
    if sql is None:
        raise ValueError(
            "The question could not be answered from the available schema. "
            "Try rephrasing or check that the referenced columns exist."
        )

    logger.info("Generated SQL: %s", sql.replace("\n", " "))
    return sql
