"""
The rubric: hard PASS/FAIL checkpoints, no partial credit.

Two kinds of checks (hybrid evaluator):
  * RULE checks  - deterministic Python. Cheap, reproducible, can't be sweet-talked.
  * LLM checks   - semantic questions (accuracy, jargon...) that code can't judge.
                   The judge must quote evidence and defaults to FAIL when unsure.

A lesson ships only if EVERY checkpoint passes.
"""
import re

from llm import complete, parse_json

REQUIRED_CONCEPTS = [
    "why plain LLMs fall short (knowledge cutoff / private data / hallucination)",
    "retrieval (finding relevant text for a question)",
    "embeddings / vector similarity search, explained simply",
    "chunking documents into pieces",
    "augmenting the prompt with retrieved text",
    "generation of the final answer grounded in that text",
]

# id -> dimension, question shown to the judge, guidance fed back to the generator
LLM_CHECKS = {
    "L1_accurate": dict(
        dim="accurate & grounded",
        q="Is every technical claim correct? FAIL if it says RAG retrains/fine-tunes model "
          "weights, says RAG eliminates hallucinations entirely, or contains any other factual error.",
        guide="Be factually precise: RAG does NOT change model weights; it adds retrieved text "
              "to the prompt at query time and REDUCES (not eliminates) hallucination."),
    "L2_grounded": dict(
        dim="accurate & grounded",
        q="Does the lesson describe the standard pipeline (index/chunk+embed -> retrieve -> "
          "augment prompt -> generate) without invented statistics, fake citations or made-up tools?",
        guide="Stick to the standard RAG pipeline; never invent numbers, papers or product claims."),
    "L3_example": dict(
        dim="teaches by example",
        q="Is there at least one concrete, worked example that follows a real question through "
          "the RAG steps (with actual sample text, not just 'imagine a question')?",
        guide="Include a worked example: a specific question, the chunks retrieved, the augmented prompt, the answer."),
    "L4_key_points": dict(
        dim="covers key points",
        q="Does it cover ALL of: " + "; ".join(REQUIRED_CONCEPTS) + "? List any missing.",
        guide="Cover all required concepts: " + "; ".join(REQUIRED_CONCEPTS) + "."),
    "L5_beginner_language": dict(
        dim="beginner-friendly language",
        q="Target learner: 12th-grade graduate from India, non-English-medium, LIMITED English vocabulary, "
          "zero ML background. FAIL if it assumes prior knowledge (transformers, fine-tuning, cosine "
          "similarity), uses idioms/slang, or uses difficult English words where a simple word works.",
        guide="Write for a 12th-pass student from India with limited English: short simple sentences, "
              "everyday words, no idioms, relatable Indian analogies (open-book exam, library)."),
    "L6_no_jargon": dict(
        dim="clear, no unexplained jargon",
        q="Is every technical term (LLM, embedding, vector, token, chunk, hallucination, "
          "index...) explained in plain words at or before its first use? Name any offenders.",
        guide="Define every technical term in plain words the first time it appears."),
    "L7_flow": dict(
        dim="coherent teaching flow",
        q="Does it build logically (problem -> idea -> how it works -> example -> recap) with no "
          "term used before it's introduced and no abrupt jumps?",
        guide="Order: problem -> core idea -> how it works step by step -> example -> recap."),
}


def _headings(md):
    return [h.lower() for h in re.findall(r"^#{1,6}\s+(.*)$", md, re.M)]


def rule_checks(md: str) -> list[dict]:
    hs, words = _headings(md), len(md.split())
    def has(pat): return any(re.search(pat, h) for h in hs)
    checks = [
        ("R1_what_why_how", "covers key points",
         has(r"\bwhat\b") and has(r"\bwhy\b") and has(r"\bhow\b"),
         "Need headings for What it is, Why it matters, and How it works.",
         "Add clearly labelled 'What is RAG?', 'Why does it matter?', 'How does it work?' sections."),
        ("R2_length", "coherent teaching flow",
         600 <= words <= 1800,
         f"Word count is {words}; must be 600-1800 (a lesson someone finishes in one sitting).",
         "Keep the lesson between 600 and 1800 words."),
        ("R3_has_recap", "coherent teaching flow",
         has(r"recap|takeaway|summary|key points"),
         "No recap / key takeaways section.",
         "End with a short 'Key takeaways' section."),
        ("R4_no_placeholders", "accurate & grounded",
         not re.search(r"TODO|\[insert|lorem ipsum", md, re.I | re.M),
         "Contains placeholder or unfinished text.",
         "No placeholders; finish every section."),
    ]
    prose = re.sub(r"```.*?```", "", md, flags=re.S)
    sents = [s for s in re.split(r"(?<=[.!?])\s+", re.sub(r"[#*>`|-]", " ", prose)) if len(s.split()) > 2]
    lens = [len(s.split()) for s in sents] or [0]
    avg, mx = sum(lens) / len(lens), max(lens)
    ok = avg <= 16 and mx <= 35
    checks.append(("R5_simple_sentences", "beginner-friendly language", ok,
                   f"Sentences too long for a limited-English reader (avg {avg:.1f} words, longest {mx}); need avg <= 16, max <= 35.",
                   "Split long sentences. Keep most between 8 and 15 words."))
    return [dict(id=i, dim=d, kind="rule", passed=p, reason="ok" if p else r, guide=g)
            for i, d, p, r, g in checks]


JUDGE_SYSTEM = """You are a strict content reviewer for beginner lessons. You do NOT write or fix
lessons. For each checkpoint return PASS or FAIL. Rules: no partial credit; if you are unsure or
cannot find clear supporting evidence in the text, FAIL. Quote the exact sentence that justifies
your verdict. Respond with ONLY a JSON object, no prose, no code fences."""


def llm_checks(md: str) -> list[dict]:
    listing = "\n".join(f'- {k}: {v["q"]}' for k, v in LLM_CHECKS.items())
    user = f"""LESSON:
<<<
{md}
>>>

CHECKPOINTS:
{listing}

Return JSON exactly like:
{{"L1_accurate": {{"passed": true, "evidence": "quoted sentence", "reason": "one line"}}, ...}}
Include every checkpoint id listed above."""
    verdict = None
    for _ in range(2):  # one retry if the judge returns junk
        try:
            verdict = parse_json(complete(JUDGE_SYSTEM, user, role="judge",
                                          temperature=0, max_tokens=2000))
            break
        except Exception:
            continue
    out = []
    for cid, meta in LLM_CHECKS.items():
        v = (verdict or {}).get(cid)
        # FAIL CLOSED: missing/unparseable judge output counts as a failure
        passed = bool(v and v.get("passed") is True)
        reason = (v or {}).get("reason", "judge output missing/unparseable (fail-closed)")
        ev = (v or {}).get("evidence", "")
        out.append(dict(id=cid, dim=meta["dim"], kind="llm", passed=passed,
                        reason=reason + (f' | evidence: "{ev}"' if ev else ""), guide=meta["guide"]))
    return out


def evaluate(md: str) -> dict:
    results = rule_checks(md) + llm_checks(md)
    failed = [r for r in results if not r["passed"]]
    return dict(passed=not failed, results=results, failed=failed)
