# Self-Evaluating Lesson Content Generator

An agentic workflow that **generates** a beginner lesson, **evaluates** it against a hard pass/fail
rubric, **regenerates** with targeted feedback on failure, and **outputs** the passing lesson plus a
rejection log. Topic for submission: **Introduction to RAG**.

## Setup & run
```bash
git clone <this-repo> && cd rag-lesson-agent
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add ONE API key (Anthropic or OpenAI)

python agent.py                                         # normal run
python agent.py --inject-error                          # demo: draft 1 contains a deliberate factual error
python agent.py --topic "Introduction to RAG"           # explicit topic
```
Outputs (in `output/`): `lesson.md` (final lesson), `rejection_log.md` / `.json` (what failed, why,
what changed on retry), `attempts/attempt_N.md` (every draft). `memory.json` persists across runs.

## Target learner
12th-grade graduate from India, non-English-medium background, limited English vocabulary, wants to
start an AI career. The generator prompt, the L5 judge check and the deterministic R5 check
(average sentence length <= 16 words, none > 35) are all tuned to this learner. Analogies use everyday
Indian contexts (open-book exam, library, asking a teacher).

## Architecture
```
            +-------------------- memory.json (past failure counts) -------------------+
            |                                                                          |
topic --> [GENERATE] --draft--> [EVALUATE: rules + LLM judge] --all pass?--yes--> lesson.md
              ^                          |                                       + rejection_log
              |                          no (failed checks + reasons + fixes)
              +---- [REGENERATE] <-------+   (max 2 retries, then flag for human review)
```
| File | Role |
|---|---|
| `agent.py` | The loop, memory read/write, rejection-log rendering |
| `rubric.py` | The 12 pass/fail checkpoints + hybrid evaluator |
| `llm.py` | Provider-agnostic wrapper (Anthropic/OpenAI), separate generator/judge models |

## The rubric (12 hard checkpoints, no partial credit)
Maps to the six required dimensions. **Any single fail = reject.**

| Dimension | Checkpoints | Type |
|---|---|---|
| accurate & grounded | L1 no factual errors (e.g. "RAG retrains the model"), L2 standard pipeline / no invented facts, R4 no placeholders | LLM, LLM, rule |
| teaches by example | L3 concrete worked example following a real question through the pipeline | LLM |
| covers key points | L4 all 6 required concepts, R1 has What / Why / How sections | LLM, rule |
| beginner-friendly language | L5 readable by a limited-English 12th-pass learner, R5 sentence-length limit | LLM, rule |
| clear, no unexplained jargon | L6 every term defined at first use | LLM |
| coherent teaching flow | L7 problem -> idea -> mechanism -> example -> recap, R2 length 600-1800 words, R3 recap section | LLM, rule |

## Design decisions & trade-offs (the "why")
1. **Generate -> evaluate -> regenerate as a loop, not one prompt.** A single prompt can't know if it
   failed. Separating the writer from the reviewer gives an independent quality gate.
2. **Hybrid evaluator (rules + LLM judge).** Structure/length checks are deterministic Python:
   free, reproducible, un-arguable. Semantic checks (accuracy, jargon) need an LLM. Using both
   avoids "LLM-only judge" flakiness while still catching meaning-level errors.
3. **Binary checkpoints, evidence required.** The judge must quote the offending sentence and is told
   to FAIL when unsure. Scores like "7/10" invite drift and rationalisation; pass/fail is auditable.
4. **Fail-closed.** If the judge returns malformed JSON, the checks count as FAILED - a broken
   evaluator can never silently approve bad content.
5. **Targeted feedback.** Regeneration receives the previous draft + exact failed checks + a concrete
   fix per check, so retries repair rather than re-roll.
6. **Bounded retries (max 2).** Guarantees termination and cost control. If still failing, the best
   draft (fewest failures) is saved with a `NEEDS HUMAN REVIEW` banner instead of pretending success.
7. **Separate generator/judge models** (`GENERATOR_MODEL` / `JUDGE_MODEL`): a model grading its own
   output is biased toward approving it; a different/stronger judge reduces that.
8. **Self-evolving memory.** Every failure increments a counter in `memory.json`. On the next run the
   most frequent failures are injected into the generator prompt as "lessons learned", so recurring
   mistakes are prevented *before* they reach the evaluator (fewer retries over time).
9. **Plain Python, no framework.** The control flow is ~100 lines; LangGraph/n8n would add moving parts
   without adding capability here. The loop maps 1:1 onto a LangGraph graph if this needs to scale.

## Known limitations / next steps
- LLM judge can still miss subtle errors -> add retrieval-grounded fact checking against trusted RAG docs.
- Memory is a simple counter; could cluster failures and rewrite the rubric/prompts automatically.
- Single topic per run; batch mode + parallel evaluation would be easy to add.
