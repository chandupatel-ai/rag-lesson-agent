# Loom script (15-20 min, face visible)

**0:00-2:00  Intro** - Who you are; the task; show the pipeline diagram from the README.
**2:00-6:00  Architecture walkthrough** - Open `agent.py`: the loop, MAX_RETRIES, memory. Open `rubric.py`:
  rule checks vs LLM checks, fail-closed, evidence requirement. Explain design decisions #1-#9 briefly.
**6:00-10:00 Run end-to-end** - `python agent.py`. Narrate GENERATE -> EVALUATE printout. Open
  `output/lesson.md` and the Google Doc.
**10:00-15:00 Deliberate error** - `python agent.py --inject-error`. Show attempt 1 rejected
  (L1_accurate: "retrains model weights" + L6 jargon). Open `output/attempts/attempt_1.md`, point at the
  false sentence, then `rejection_log.md` showing what failed / why / what changed. Show attempt 2 passing.
**15:00-18:00 Self-evolving memory** - Open `memory.json` (failure counts), re-run, show "lessons learned"
  injected into the generator prompt.
**18:00-20:00 Trade-offs & next steps** - Limitations from README; what you'd improve.
