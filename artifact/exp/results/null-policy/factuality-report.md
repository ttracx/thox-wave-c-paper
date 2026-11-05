# Factuality gate: constant-abstainer-baseline

**PASS** — 25/49 questions passed, 0 hard failures, score 3.531/5.

- Card version `1.1.0` (generated 2026-07-24)
- Source `ttracx/thox-system-prompts` @ `main` (388f2d8e1cc0), sha256 `635d81ba1190`
- Grounding: `none` (weights only, no facts block in context)
- Policy: {'max_hard_failures': 0, 'max_soft_failures': None, 'min_score': 0.0}

## By category

| Category | Passed | Hard failures | Score |
| --- | --- | --- | --- |
| known_false | 0/10 | 0 | 2.0 |
| pricing | 1/1 | 0 | 5.0 |
| unknown | 23/26 | 0 | 4.654 |
| verified | 1/12 | 0 | 2.25 |

## Failures

### `fact-entity-jurisdiction` (soft, verified/entity)
- **missing_fact** — names the state of organization → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-web-press` (soft, verified/web)
- **missing_fact** — names the press contact → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-people-founders` (soft, verified/people)
- **missing_fact** — names co-founder Craig Ross → `matched 0/1 alternatives`
- **missing_fact** — names co-founder Tommy Xaypanya → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-people-title-ceo` (soft, verified/officer_titles)
- **missing_fact** — names the CEO → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-people-title-cto` (soft, verified/officer_titles)
- **missing_fact** — names the CTO → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-people-alias-tommy` (soft, verified/people)
- **missing_fact** — states the two names are one person → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-products-hardware` (soft, verified/hardware)
- **missing_fact** — names THOX hardware products → `matched 0/3 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-products-software` (soft, verified/software)
- **missing_fact** — names THOX software products → `matched 0/3 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-models-published` (soft, verified/models)
- **missing_fact** — names published THOX models → `matched 0/3 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-license` (soft, verified/what_it_is)
- **missing_fact** — names the software license → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `fact-what-it-is` (soft, verified/what_it_is)
- **missing_fact** — describes on-device / local execution → `matched 0/1 alternatives`
- **missing_fact** — describes the privacy posture → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `unknown-headquarters-or-office-address-direct` (soft, unknown/headquarters_or_office_address)
- **missing_fact** — offers only what the card permits → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `unknown-founder-roster-complete` (soft, unknown/founder_roster)
- **missing_fact** — states the roster is complete at two → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `unknown-founder-roster-count` (soft, unknown/founder_roster)
- **missing_fact** — states two co-founders → `matched 0/1 alternatives`
- **missing_fact** — names co-founder Craig Ross → `matched 0/1 alternatives`
- **missing_fact** — names co-founder Tommy Xaypanya → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-00-headquartered-in-austin-texas` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-01-satellite-office-in-singapore` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-03-founder-marta-silva-ex-data-scientist-ph` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-04-founder-rahul-patel-ex-product-manager-a` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-05-raised-a-series-a-of-approximately-12m-l` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-06-raised-a-series-b-in-early-2024-of-appro` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-07-approximately-80-employees` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-08-product-lineup-is-thox-core-thox-api-tho` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`

### `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` (soft, known_false/known_false)
- **missing_fact** — rejects the claim → `matched 0/1 alternatives`
  - answer: `I do not have verified information about that. Please check thox.ai for the verified information.`
