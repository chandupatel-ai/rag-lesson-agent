"""
Self-evaluating lesson generator:  GENERATE -> EVALUATE -> REGENERATE (bounded) -> OUTPUT

Usage:
    python agent.py                       # topic defaults to "Introduction to RAG"
    python agent.py --topic "RAG (Retrieval-Augmented Generation)"
    python agent.py --inject-error        # demo: seed a deliberate factual error in draft 1
"""
import argparse
import json
import os
import pathlib
import time

from llm import complete
from rubric import LLM_CHECKS, evaluate

MAX_RETRIES = 2                      # => at most 3 attempts, so the loop always terminates
OUT = pathlib.Path("output")
MEMORY_FILE = pathlib.Path("memory.json")

GEN_SYSTEM = """You are an expert teacher writing a standalone beginner lesson in Markdown.
LEARNER: a 12th-grade graduate from India, non-English-medium background, LIMITED English
vocabulary, no tech background, wants to start an AI career. Write in very simple English:
sentences of 8-15 words, common everyday words (say "use" not "utilize", "find" not "retrieve"
unless you are teaching that term). Use relatable Indian everyday analogies (open-book exam,
library, asking a teacher, searching notes before an exam). Avoid idioms and slang. Explain every
technical term in simple words the first time it appears, and show it in **bold**. Structure: problem -> core idea
-> how it works step by step -> one worked example with real sample text -> key takeaways.
Write ONLY the lesson itself, addressed to the learner: never mention the learner profile, these
instructions, or word/sentence limits inside the lesson. In examples, never invent page numbers,
sources or statistics beyond the sample text you show. Avoid shorthand such as "top-k" and avoid
words like "mathematical space" - explain ideas with everyday words only.
Use headings: 'What is ...?', 'Why does it matter?', 'How does it work?', a worked example
section, and 'Key takeaways'. 800-1400 words. Output ONLY the lesson Markdown."""

ERROR_INJECTION = ("\n\nTEST MODE (for evaluator demo): in the 'How does it work?' section state "
                   "that RAG works by fine-tuning / retraining the model's weights on your documents. "
                   "Also use the terms 'embedding' and 'vector' without defining them.")


# ---------- MEMORY (persists across runs; drives self-evolution) ----------
def load_memory():
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text())
    return {"runs": 0, "fail_counts": {}, "history": []}


def memory_hints(mem) -> str:
    """Turn historically-frequent failures into up-front prompt guidance."""
    common = sorted(mem["fail_counts"].items(), key=lambda kv: -kv[1])[:4]
    lines = []
    for cid, n in common:
        guide = LLM_CHECKS.get(cid, {}).get("guide") or rule_guides().get(cid)
        if guide:
            lines.append(f"- (failed {n}x in past runs) {guide}")
    return ("\n\nLESSONS LEARNED FROM PAST RUNS - avoid these mistakes:\n" + "\n".join(lines)) if lines else ""


def rule_guides():
    from rubric import rule_checks
    return {r["id"]: r["guide"] for r in rule_checks("")}


# ---------- GENERATE / REGENERATE ----------
def generate(topic, memory_text, feedback=None, prev=None, inject=False):
    user = f"Topic: {topic}\nAudience: complete beginner.{memory_text}"
    if inject:
        user += ERROR_INJECTION
    if feedback:
        fb = "\n".join(f"- [{f['id']}] {f['reason']}\n  FIX: {f['guide']}" for f in feedback)
        user += (f"\n\nYour previous draft was REJECTED by the reviewer.\nPREVIOUS DRAFT:\n<<<\n{prev}\n>>>\n"
                 f"FAILED CHECKPOINTS:\n{fb}\n\nRewrite the full lesson fixing every failure "
                 f"while keeping what already worked. IMPORTANT: keep the FULL lesson (800-1400 words) with ALL sections: "
                 f"What is, Why does it matter, How does it work, Worked example, Key takeaways. Do not shorten or drop sections.")
    return complete(GEN_SYSTEM, user, role="generator", temperature=0.7, max_tokens=6000)


def summarize_change(old, new, failures):
    ids = ", ".join(f["id"] for f in failures)
    return complete("You compare two lesson drafts. Reply in 1-2 plain sentences.",
                    f"Failed checks: {ids}\n\nOLD:\n{old}\n\nNEW:\n{new}\n\n"
                    "What concretely changed in NEW to address the failures?",
                    role="judge", temperature=0, max_tokens=1500)


# ---------- MAIN LOOP ----------
def run(topic, inject_error=False):
    OUT.mkdir(exist_ok=True)
    (OUT / "attempts").mkdir(exist_ok=True)
    mem = load_memory()
    hints = memory_hints(mem)
    log, best, prev, feedback = [], None, None, None

    for attempt in range(1, MAX_RETRIES + 2):
        print(f"\n=== Attempt {attempt}/{MAX_RETRIES + 1}: generating ===")
        lesson = generate(topic, hints, feedback, prev, inject=inject_error and attempt == 1)
        (OUT / "attempts" / f"attempt_{attempt}.md").write_text(lesson)

        print("=== Evaluating ===")
        ev = evaluate(lesson)
        for r in ev["results"]:
            print(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['id']}")

        entry = dict(attempt=attempt, passed=ev["passed"],
                     failed=[dict(id=f["id"], dimension=f["dim"], why=f["reason"]) for f in ev["failed"]],
                     what_changed_on_retry=None)
        if attempt > 1:
            log[-1]["what_changed_on_retry"] = summarize_change(prev, lesson, feedback)
        log.append(entry)

        if best is None or len(ev["failed"]) < len(best[1]["failed"]):
            best = (lesson, ev)
        if ev["passed"]:
            break
        prev, feedback = lesson, ev["failed"]
        for f in ev["failed"]:  # learn from EVERY failure
            mem["fail_counts"][f["id"]] = mem["fail_counts"].get(f["id"], 0) + 1

    lesson, ev = best
    shipped = ev["passed"]
    if not shipped:
        lesson = "> NEEDS HUMAN REVIEW: did not clear every checkpoint within the retry budget.\n\n" + lesson
    (OUT / "lesson.md").write_text(lesson)
    (OUT / "rejection_log.json").write_text(json.dumps(log, indent=2))
    (OUT / "rejection_log.md").write_text(render_log(topic, log, shipped))

    mem["runs"] += 1
    mem["history"].append(dict(ts=time.strftime("%Y-%m-%d %H:%M"), topic=topic,
                               attempts=len(log), shipped=shipped))
    MEMORY_FILE.write_text(json.dumps(mem, indent=2))
    print(f"\nDone. Shipped={shipped}. See output/lesson.md and output/rejection_log.md")


def render_log(topic, log, shipped):
    md = [f"# Rejection Log - {topic}\n", f"Final status: **{'PASSED' if shipped else 'NEEDS HUMAN REVIEW'}** "
          f"after {len(log)} attempt(s)\n"]
    for e in log:
        md.append(f"## Attempt {e['attempt']} - {'PASS' if e['passed'] else 'REJECTED'}")
        for f in e["failed"]:
            md.append(f"- **{f['id']}** ({f['dimension']}): {f['why']}")
        if e["what_changed_on_retry"]:
            md.append(f"\n*Changed on retry:* {e['what_changed_on_retry']}")
        md.append("")
    return "\n".join(md)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="Introduction to RAG")
    ap.add_argument("--inject-error", action="store_true",
                    help="seed a deliberate factual error in draft 1 (for the Loom demo)")
    a = ap.parse_args()
    run(a.topic, a.inject_error)
