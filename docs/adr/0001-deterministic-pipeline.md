# ADR-0001: Deterministic analysis pipeline
Status: accepted

Decision: keep market analysis independent of Telegram and make each stage deterministic: validation -> indicators -> pivots/structure -> Fibonacci/Elliott -> scoring -> plan -> rendering.

Reason: the assignment requires reproducibility, testability and byte-stable analysis text for identical inputs. Telegram remains an orchestration/UI layer.
