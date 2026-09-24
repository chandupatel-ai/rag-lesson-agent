"""Thin provider-agnostic LLM wrapper (Anthropic or OpenAI) + robust JSON parsing."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
DEFAULTS = {"anthropic": "claude-sonnet-4-6", "openai": "gpt-4o"}


def complete(system: str, user: str, *, role: str = "generator",
             temperature: float = 0.7, max_tokens: int = 3000) -> str:
    """role='generator' or 'judge' -> lets you use different models for each."""
    model = os.getenv(f"{role.upper()}_MODEL") or DEFAULTS[PROVIDER]
    if PROVIDER == "anthropic":
        from anthropic import Anthropic
        r = Anthropic().messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}])
        return r.content[0].text
    from openai import OpenAI
    r = OpenAI().chat.completions.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return r.choices[0].message.content


def parse_json(text: str):
    """Extract JSON even if the model wraps it in ``` fences or adds chatter."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise
