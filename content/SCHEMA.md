# Module schema

Each built module is `content/modules/<id>.py` exposing `MODULE: dict`:

| key | contents |
|---|---|
| `summary` | one paragraph: what the module leaves you able to do |
| `concepts` | list of `{title, why, how, code, impact}`. `why`/`how`/`impact` are Markdown (LaTeX allowed). `code` is a minimal runnable example. |
| `lens` | practitioner lens: `{look, decision, justified, mistakes: [..], impact, test}` |
| `claims` | `{id, tag: M/S/J, text, source?, time_sensitive?, last_verified?, check?}`. `check` is Python run by the self-test for Measured claims. Reference in text as `{{c:id}}`. |
| `lab` | `{id, title, hypothesis, thresholds, data, code, report_hints}`. Code uses `qlab_helpers` (SEED, show, record, table). |
| `quiz` | 10–15 items: `{id, type: mc/short, q, options, answer, explain, must, tags}`. `must` = concept groups (lists of synonyms) for short answers. |
| `exercise` | `{id, title, prompt, starter, solution, tests}`. `tests` defines `test_*` functions. |
| `cards` | 10–20 `{front, back, kind}`; kind ∈ definition, formula, number, mistake |
| `defend` | `{persona, questions: [{q, must, model}]}` — 5 questions |
| `glossary` | `{term: definition}` |

Honesty rules: every factual claim gets a tag; time-sensitive Sourced claims carry `last_verified`
and are flagged after six months; implementation checks are never presented as value claims.
