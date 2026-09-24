"""Thin provider-agnostic LLM wrapper (Anthropic / OpenAI / Groq) + robust JSON parsing."""
import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
DEFAULTS = {"anthropic": "claude-sonnet-4-6", "openai": "gpt-4o",
            "groq": "openai/gpt-oss-120b"}


def _call(system, user, model, temperature, max_tokens):
    if PROVIDER == "anthropic":
        from anthropic import Anthropic
        r = Anthropic().messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}])
        return r.content[0].text
    from openai import OpenAI
    extra = {}
    if PROVIDER == "groq":  # Groq exposes an OpenAI-compatible API
        client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                        base_url="https://api.groq.com/openai/v1")
        if "gpt-oss" in model:  # reasoning model: keep "thinking" short so output isn't cut off
            extra = {"reasoning_effort": "low"}
    else:
        client = OpenAI()
    r = client.chat.completions.create(
        model=model, temperature=temperature, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        extra_body=extra or None)
    if r.choices[0].finish_reason == "length":
        print("  (warning: model output was cut off at max_tokens)")
    return r.choices[0].message.content or ""


def complete(system: str, user: str, *, role: str = "generator",
             temperature: float = 0.7, max_tokens: int = 3000) -> str:
    """role='generator' or 'judge' -> lets you use different models for each."""
    model = os.getenv(f"{role.upper()}_MODEL") or DEFAULTS[PROVIDER]
    for attempt in range(6):  # free tiers rate-limit: wait and retry
        try:
            return _call(system, user, model, temperature, max_tokens)
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 15 * (attempt + 1)
                print(f"  (rate limit hit, waiting {wait}s...)")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Rate limit: gave up after 6 retries")


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
