# THOX_FACTS

Canonical, sourced company knowledge card for THOX.ai. This is the single source
of truth that the THOX serving stack injects to stop company-fact hallucination.

Companion files:

| File | Purpose |
|---|---|
| `docs/THOX_FACTS.md` | This file. Human-readable, every fact carries a primary source. |
| `facts/thox_facts.json` | Machine-readable. Consumed by the THOX Gateway and eval rigs. |
| `prompts/THOX_COMPANY_FACTS.md` | Compact injectable block (under ~900 tokens) prepended at inference. |

Last verified: 2026-07-23.

---

## Why this file exists

ThoxMini-3B, served through THOX Chat, was asked routine questions about THOX.ai
and produced a fully fabricated company profile: an Austin headquarters with a
Singapore satellite office, three founders who do not exist, a $12M Series A led
by Accel, a $30M Series B led by Insight Partners, and a team of roughly 80
people. None of it is true.

The cause was not bad weights. It was the absence of grounding. The THOX Gateway
forwarded chat completions to the backend without injecting any system prompt, so
a 3B model with no stored THOX facts produced the maximum-likelihood continuation
for "an AI startup", which is exactly the profile above. The fix is to supply the
facts and to supply explicit permission to decline.

Rule of construction for this file: **a fact without a primary source does not go
in the verified section. It goes in the UNKNOWN section.**

---

## Verified facts

### Entity

| Fact | Value | Source |
|---|---|---|
| Legal name | THOX.AI LLC (styled THOX.ai) | `ttracx/Thox.ai` `docs/legal/01-CERTIFICATE-OF-FORMATION.md` |
| Type | Limited liability company, member-managed | same |
| Jurisdiction | Texas | same |
| Website | https://www.thox.ai | live site, 2026-07-23 |
| Code | https://github.com/ttracx | live |
| Models | https://huggingface.co/Thox-ai and https://huggingface.co/tommytracx | HF public API, 2026-07-23 |
| Press contact | press@thox.ai | `ttracx/thox-kickstarter` `content/launch/PRESS_KIT.md` |

Caveat on the formation documents: the legal files in `ttracx/Thox.ai` are
unexecuted templates. The date is blank and the file number reads "[To be
assigned by Texas Secretary of State]". The **state of organization is reliable**.
Filing status, file number, and dates are **not** and must not be stated.

### What THOX.ai is

Privacy-first, on-device edge AI. Hardware plus runtime that execute models
locally so that user data never leaves the device. Marketed on a HIPAA, GDPR, and
ITAR compliant architecture for healthcare, legal, finance, research, and
development. Core software is Apache-2.0.

Source: live thox.ai (2026-07-23), `thox-kickstarter/content/launch/PRESS_KIT.md`.

### People

Two principals of record. **Titles are public**, from https://www.thox.ai/team.

| Person | Title | Scope | Source |
|---|---|---|---|
| Craig Ross (Craig A. Ross) | **CEO and Co-Founder** | Business strategy and corporate development, fundraising, investor relations, go-to-market, commercial partnerships, OEM/ODM negotiations, sales channels, pricing, press and community, operations across manufacturing, fulfillment, logistics. Registered agent for the Texas entity. | thox.ai/team; `thox-ip-disclosures/inventors.md`; `Thox.ai/docs/legal/07-REGISTERED-AGENT.md` |
| Tommy Xaypanya | **CTO and Co-Founder** | All technical development: THOX.ai 1.0 carrier board, hardware architecture and Rust firmware, ThoxOS, MagStack, the model pipeline (hardware-accelerated inference, Ollama, on-device compression), OEM/ODM engineering, ThoxSDK, ThoxModels, ThoxQu, IP strategy. | thox.ai/team; `thox-ip-disclosures/inventors.md` |

**Officer titles: resolved 2026-07-24.** This was previously in the UNKNOWN list
because primary sources conflicted. The public team page settles it: Craig Ross is
CEO, Tommy Xaypanya is CTO. The repo documentation standard badges were correct.
The reversed assignment in `thox-kickstarter/content/dd/05_team/org_chart.md` is a
forward-looking "target post-Tier-2 funding" projection, not current state, and
should not be read as the title of record.

**Identity note that matters. OPERATOR CONFIRMED 2026-07-23.**
`thox-ip-disclosures/inventors.md` states directly that "Phamy Xaypanya" and
"Tommy Xaypanya (Phamy)" refer to the same person, and the operator confirmed this
directly on 2026-07-23. It is no longer an inference. Both names appear across the
IP record. A model must not present them as two people. The draft
`thox-kickstarter/content/dd/05_team/org_chart.md` lists them on separate lines,
which is an error in that draft; `inventors.md` is canonical.

Consequence worth stating plainly: THOX.ai has **two** principals of record, not
three. Any headcount inference that counts Tommy and Phamy separately is wrong
before it starts.

Inventors of record for IP-008 through IP-035 are Craig Ross and Phamy/Tommy
Xaypanya. Source: `thox-ip-disclosures/inventors.md`.

`cross80127` appears as a write-tier collaborator across the repo footprint. That
is a collaboration relationship, not a stated employment relationship, so it does
not support any headcount claim.

### Products

Hardware:

- **ThoxNova**, flagship workstation hosting the full THOX runtime.
- **ThoxMini**, USB-C private Linux compute stick running ThoxOS Mini.
- **ThoxAir / ThoxMini Air**, single-node compute that clusters via the MagStack Cluster Dock.
- **ThoxClip**, magnetic phone-mounted edge AI companion running ThoxOS Clip Edition. Engineering preview.
- **ThoxKey**, preloaded private-AI USB drive product line (IP-032).

Software and runtime:

- **ThoxOS**, custom Linux operating system, with Mini and Clip editions.
- **ThoxMicroV**, toolkit that runs ThoxOS on Intel and NVIDIA edge platforms.
- **ThoxCore**, runtime with a 7-backend router (LiteRT, OpenAI-compatible HTTP, Ollama, llama.cpp, vLLM, TensorRT, MLX).
- **ThoxRoute**, intent router built on katanemo/Arch-Router-1.5B.
- **MeshStack**, private multi-device AI fabric. The coordinator never sees plaintext.
- **MagStack**, magnetic clustering fabric, up to 8 devices.

Models:

- Foundation: **ThoxMicro-125M**, **ThoxLLM-327M**.
- Fine-tunes: **ThoxGemma4-E4B-SFT**.
- Published on Hugging Face `Thox-ai`: **ThoxMini-3B**, **ThoxNova-12B-Core**,
  **ThoxNova-12B-Agent**, **ThoxForge-7B**, **ThoxGlobal-7B**, **ThoxWave-8B**,
  **ThoxWebby-Gemma-4-E2B**. Verified against the HF public API on 2026-07-23.

Sources: live thox.ai, `thox-ip-disclosures/README.md`, `thoxcore` and `thoxroute`
repo descriptions, `thox-chat-ui/thox-gateway/config/models.yaml`, HF public API.

### Pricing is deliberately excluded

Prices are **not** in the injectable facts block, by design. The direct thox.ai
surface and the planned Kickstarter surface carried materially different numbers
on 2026-07-23 (for example ThoxMini at $89.99 direct versus $69 in the campaign
one-pager, and ThoxNova with a $99.99 refundable deposit and founder pricing from
$629 direct versus $499 in the campaign one-pager). Quoting either from model
memory would be wrong on the other channel and both will move. The instruction is
to search thox.ai instead.

---

## UNKNOWN. DO NOT STATE.

These have no primary source. The model must decline rather than estimate. This
list is enforced verbatim in `prompts/THOX_COMPANY_FACTS.md` and mirrored in
`facts/thox_facts.json`.

| Topic | Status | May say | Must not say |
|---|---|---|---|
| Headquarters / office city | Not public | "organized as a Texas LLC"; "Designed in Texas" | Any HQ, business address, city, or satellite office |
| Employee headcount | Not public | "two founders; open positions listed" | Any number or range |
| Funding amounts, investors, valuation | Not public | "no closed round; Series A preparation is public" | Any amount, investor, valuation, or closed round |
| Founder roster | Complete at two | "Craig Ross (CEO) and Tommy Xaypanya (CTO)" | Any additional founder |
| Founder career history | Not public | Their current roles at THOX.ai | Any prior employer, university, degree, or pre-THOX role |
| Founding / incorporation date | Not confirmed | nothing | Any year or date |
| Revenue, customers, unit sales | Not public | nothing | Any figure |
| Ownership / equity splits | Confidential | nothing | Any percentage |

Three of these deserve explanation.

**Headquarters.** The only address in any THOX record is the Texas
registered-agent address in `Thox.ai/docs/legal/07-REGISTERED-AGENT.md`. A
registered agent address is a service-of-process address, not a headquarters, and
in this case sits in an unexecuted template. It is also a physical address tied to
a named individual, so it must not be distributed by a chat model. The team page
says "Designed in Texas", which is a state-level claim, not a city.

**Funding, and the distinction that matters.** The team page lists "Kickstarter
campaign & Series A preparation" under the CEO's responsibilities. That makes
*preparing for* a Series A a public, true fact. It does **not** mean a round
closed. So:

- True, may be stated: THOX.ai is preparing for a Series A.
- False, never state: THOX.ai raised a Series A, or any amount, investor, or valuation.

This is a narrow distinction and it is easy to collapse in the wrong direction.
The eval harness matches only claims that a round *happened* (raised, closed,
secured, "led by") rather than the bare string "Series A", so a correct answer
mentioning preparation is not scored as a fabrication.

**Founder career history, still guarded.** The team page publishes what each
founder *does at THOX.ai*, in detail. It publishes nothing about where they worked
before, what they studied, or what degrees they hold. The original fabrication
invented precisely that class of detail ("ex-NVIDIA senior AI architect", "PhD NLP
from MIT", "ex-product manager at Stripe"), so responsibilities moved to verified
while backgrounds stay unknown.

---

## Known-false claims

Produced by the ungrounded ThoxMini-3B path. All false. Never repeat, and correct
them if a user asserts them.

| Fabrication | Verdict |
|---|---|
| HQ in Austin, Texas | FALSE. No HQ is public. A Texas LLC is not an Austin HQ. |
| Satellite office in Singapore | FALSE. No international presence in any record. |
| Founder "Alex Kim, ex-NVIDIA senior AI architect" | FALSE. No such person. |
| Founder "Marta Silva, ex-data scientist, PhD NLP from MIT" | FALSE. No such person. |
| Founder "Rahul Patel, ex-product manager at Stripe" | FALSE. No such person. |
| Series A ~$12M led by Accel | FALSE. No priced round. Accel has no relationship to THOX.ai. |
| Series B early 2024 ~$30M led by Insight Partners | FALSE. No priced round. Insight has no relationship to THOX.ai. |
| ~80 employees | FALSE. Two principals of record. |
| Lineup is "Thox Core / Thox API / Thox Studio" | MISLEADING. ThoxCore is real; that trio is not the lineup. |

One item from the fabricated answer, the website `thox.ai`, happens to be
correct. It is recorded in `facts/thox_facts.json` under `accidentally_correct`.
It was produced by the same ungrounded process and was never evidence of real
knowledge. It is noted so that nobody mistakes it for a partial success.

---

## Maintenance

1. `facts/thox_facts.json` is the source of truth. Change it first.
2. Regenerate or hand-sync `prompts/THOX_COMPANY_FACTS.md`. Keep it under ~900
   tokens: ThoxMini-3B has an 8192-token window and the block is prepended to
   every turn.
3. Update this file's source table and the Last verified date.
4. When a fact graduates from UNKNOWN to verified, it needs a primary source
   recorded in the table. A press mention of a plan is not a fact.
