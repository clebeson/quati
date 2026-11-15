# S00 independent review resolution

The independent reviewer reproduced three defects in the candidate. Parent integration
added three discriminating tests first; `evidence/S00/independent_regression_red.txt`
records all three failing. Fixes were then applied:

1. No-result advisory classifications no longer produce successful user-visible answers.
   Only deterministic greetings and actual validated synthetic fixture findings return
   success in S00. Model prose cannot establish completed work. This deliberately limits
   informational replies until S01 evaluation.
2. start/resume/deepen/review action edges require exact lifecycle-stage and guard tuples.
   The reference compiler and packaged S00 copy remain byte-equivalent except resource
   root and descriptive docstring. This is static protection; production commitment
   statecharts remain quarantined until S02 transactional/recovery validation.
3. One endpoint validator serves doctor and model transport, rejecting invalid ports,
   URL credentials, whitespace, query, fragment and non-HTTPS URLs.

Regression results: `evidence/S00/independent_regression_green.txt`. The original review
is retained unchanged. This parent resolution is not a new independent certification.
No live LLM call was made; S00 L3 remains BLOCKED.
