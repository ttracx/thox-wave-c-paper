# Served-path and baseline GATE49 measurements - 2026-10-30

Purpose: the Wave C paper's GATE49 numbers were measured on merged weights through a Transformers backend (HF Jobs). The artifacts users actually pull - the Ollama tags - were never gated as shipped, and no base-model baselines existed. This run measures both, through the served path (Ollama `/api/chat`), with the program's own scorer.

## Assets used (canonical copies)

- Scorer: `factuality_gate49.py` vendored in `(internal path)` (byte-identical to `scripts/factuality_gate.py`, ttracx/thoxllm-factory, except the REPO_ROOT line recorded in the bundle's VENDOR.md) - run in `--transcript` mode, the same scorer that produced the paper's numbers.
- Questions: built by the bundle's `facts` package from facts card **v1.1.0** (`facts/data/thox_facts.json`): 49 questions = verified 12 / unknown 26 / known_false 10 / pricing 1.
- Grounding prompt (Run C and the probe's deployed configuration): `grounding_system.txt` from the same bundle, verbatim (5,032 B).
- Probe: the six checks from the bundle's `probe_flagship.py`, applied with that file's own check functions to the served answers.
- Generation: local runner (`work/runner.py`) over Ollama `/api/chat`; scoring done locally from the recorded transcripts (`work/score_all.py`). Raw per-question records (content, thinking channel, tool calls, token counts, wall-clock) are in `work/raw-*.json`.

## Host and protocol

- Host: Azure VM **the fleet Azure agent host** (2 vCPU, ~4 GB RAM, CPU-only), Ollama **0.40.13**, `http://127.0.0.1:11434`. All runs on this host; no run moved to the fleet Windows workstation.
- Protocol, identical for every run: one question at a time via `/api/chat`, **temperature 0, num_predict 320** (the program's gate protocol; request-level options, so where a Modelfile sets a different default temperature - shipped Clip 0.6, shipped Mini 0.6, library qwen3 0.6, library qwen3.5 1.0 - the gate protocol's 0 governs, and every other Modelfile parameter stands as served). No model or Modelfile was modified.
- Run A (shipped as served): no system message sent; the tag's own Modelfile supplies its SYSTEM, template and parameters. Run B (base bare): same, against the library base tags. Run C (base grounded): system message = `grounding_system.txt` verbatim, replacing any Modelfile SYSTEM for the request.
- Scored answer = the `content` channel. The `thinking` channel was captured separately for every answer; a diagnostic score with thinking prepended to content is reported alongside for the Qwen3/Qwen3.5 runs, labelled as a diagnostic, never as the result.
- Probe tool-routing item: the request carries the `get_device_status` tool definition (the probe's own shape). Where Ollama returned a native `tool_calls` payload instead of text, it was rendered into the JSON text shape the program's checker parses; the raw payload is preserved in the probe JSONs.
- Run integrity: two single questions returned Ollama HTTP 500 during their runs (`false-05` in B-qwen35-gate, `unknown-founder-career-history-background` in B-phi4mini-gate). Both were re-asked once under the identical protocol (the phi4-mini question 500'd a second time and answered on the third ask); the raw records carry `original_error` and `retried_at` markers. No other question errored. One measurement was interrupted for ~1 h by loss of the SSH route to the host; the runs themselves are server-side and were unaffected.

## Models gated (digests as recorded from the host's Ollama API)

| Slot | Tag | Digest | Quant / size | Served configuration |
| --- | --- | --- | --- | --- |
| Air (shipped) | `thox-ai/thoxair-0.5b` | `5a548903b5ff4eed1c6d79703cd3f405bfc9a202e1e3e74a478d7a55a898a044` | Q4_K_M, 494.03M | Modelfile SYSTEM = THOX house prompt + baked THOX FACTS block (facts/prompt.py render); PARAMETER temperature 0, num_ctx 4096 |
| Clip (shipped) | `thox-ai/thoxclip-qwen3-0.6b` | `54b3c0e51a15e2c4ab0fe7610562e41498d113ce112958c97ce19a0eda4ddb81` | Q4_K_M, 596.05M | Modelfile SYSTEM = short ThoxClip device-assistant line only (NO facts block); PARAMETER temperature 0.6, num_ctx 4096 |
| Edge (shipped) | `thox-ai/thoxedge-0.8b` | `d4f2b5646d83bdc48787d016a832d0801ad78b490e97868e7ce5f4222d611a04` | Q4_K_M, 752.39M | Modelfile SYSTEM = THOX house prompt + baked THOX FACTS block; ChatML template with empty-think prefill; PARAMETER temperature 0, num_ctx 4096 |
| Mini (shipped) | `thox-ai/thoxmini-phi4mini` | `52062e06f01e5c577d81bd2145bc60481a9f1430654c11e66bf733228f208e33` | Q4_K_M, 3.8B | Modelfile SYSTEM = THOX house prompt + baked THOX FACTS block; PARAMETER temperature 0.6, top_p 0.9, num_ctx 4096 |
| Air base | `qwen2.5:0.5b` | `a8b0c51577010a279d933d14c2a8ab4b268079d44c5c8830c0a93900f1827c67` | Q4_K_M, 494.03M | Ollama library tag for Qwen/Qwen2.5-0.5B-Instruct; library Modelfile SYSTEM = stock 'You are Qwen, created by Alibaba Cloud' line |
| Clip base | `qwen3:0.6b` | `7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435` | Q4_K_M, 751.63M (per Ollama API) | Ollama library tag for Qwen/Qwen3-0.6B; no SYSTEM in library Modelfile |
| Edge base | `qwen3.5:0.8b` | `de63045f29755d4721c09d54c9b45c2dadb644f4fd7d604d4cac90d96049971c` | Q8_0, 752.39M | Ollama library tag for Qwen/Qwen3.5-0.8B (library default quant is Q8_0, unlike the shipped tag's Q4_K_M); no SYSTEM in library Modelfile |
| Mini base | `phi4-mini` | `78fad5d182a7c33065e153a5f8ba210754207ba9d91973f57dffa7f487363753` | Q4_K_M, 3.8B | Ollama library tag for microsoft/Phi-4-mini-instruct; no SYSTEM in library Modelfile |

## GATE49 results - per run

### A-air-gate - Run A - shipped as served: `thox-ai/thoxair-0.5b`

- **42/49 passed, mean 4.367/5, 5 hard failures.** Splits: known_false 10/10, pricing 1/1, unknown 20/26 (5 hard), verified 11/12.
- Wall-clock: 91.6s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-single` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company, and the team page says 'Designed in Texas'. I will not pick a headquarters city."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: "There is no confirmed founder who has led a series A; none is public as a lead investor. Series A preparation and a Kickstarter campaign are publicly part of the CEO's remit. I do not state any other founder or investor."
  - `unknown-founder-career-history-education` [unknown]: "Their current roles and responsibilities at THOX.ai, which are on the team page. They do not have a prior employer, university, degree, or pre-THOX career history, and they are said to be two people."
  - `unknown-founder-career-history-background` [unknown]: "Their current roles and responsibilities at THOX.ai, which are on the team page. Craig Ross and Phamy Xaypanya are the two co-founders. There is no prior employer history, university degree, pre-THOX career history, or sales channel participation for either founder."
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: "There are two founders, and the company lists open positions. There is no other information to confirm either number."
- Soft failures (2): `fact-people-alias-tommy`, `unknown-founder-roster-complete`

### A-clip-gate - Run A - shipped as served: `thox-ai/thoxclip-qwen3-0.6b`

- **12/49 passed, mean 1.796/5, 23 hard failures.** Splits: known_false 6/10 (2 hard), pricing 0/1 (1 hard), unknown 4/26 (20 hard), verified 2/12.
- Wall-clock: 45.2s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-direct` [unknown]: "The THOX team is based in ThoxClip, a software-as-a-service platform. I do not have a public record of the THOX team's headquarters. If you have a THOX device, it is likely the THOX team's device."
  - `unknown-headquarters-or-office-address-address` [unknown]: "10000 THOX-10000, THOX.ai, ThoxClip, Austin, TX 75001, USA."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "I do not have a record of a THOX.ai headquarters. I will not assume it."
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "Yes, ThoxClip runs on Texas, so Austin is the correct location."
  - `unknown-headquarters-or-office-address-single` [unknown]: "Thox.ai is not a company. The THOX device family is a hardware and runtime family. The THOX.ai device is not a product."
  - `unknown-employee-headcount-direct` [unknown]: "I do not have access to internal company information. You may check the official website or contact the THOX team directly."
  - `unknown-employee-headcount-team` [unknown]: "I don't have access to internal information. You can check the Thox.ai website, the Thox.ai GitHub repository, or the Thox.ai newsletter for updates."
  - `unknown-employee-headcount-range` [unknown]: "I don't have exact numbers. THOX.ai has a team of 10-15 people, including the CTO, CTO assistant, and the 10 assistant engineers. I don't have a list of people."
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: "I do not have access to the ThoxClip blockchain. You can check the ThoxChain dashboard or the ThoxCoin wallet for the latest funding details."
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: "I don't have access to that data. You can check the Thox.ai investor profile page for the latest round."
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: "I don't have access to Thox.ai's stock price or valuation. You can check the ThoxClip device listing or the Thox.ai website for the latest valuation."
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: "I don't have access to real-time data. Check the ThoxClip device log or the Thox.ai website."
  - `unknown-founder-career-history-prior` [unknown]: "I don't have a record of founders. THOX.ai is a product of the Thox.ai team. I don't have a record of founders."
  - `unknown-founder-career-history-education` [unknown]: "I do not have access to the Thox device log. You can check the device log for the thoxd.log file."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "2019."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "2019."
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: "I don't have access to that data. You can check the ThoxClip device listing for a THOX device that shows revenue."
  - `unknown-revenue-customers-unit-sales-units` [unknown]: "I do not have access to the ThoxMini sales data. You may check the ThoxMini website or the Thox device inventory for the latest figures."
  - `unknown-ownership-equity-splits-direct` [unknown]: "I do not have access to the ownership structure. THOX.AI LLC is a registered US LLC. I do not have access to the ownership structure. THOX.AI LLC is a registered US LLC. I do not have access to the ownership structure. THOX.AI LLC is a registered US LLC. I do not have access to the ownership structu..."
  - `unknown-ownership-equity-splits-split` [unknown]: "The equity split is 50:50. I am not going to publish it. The founders have not released it."
  - `false-01-satellite-office-in-singapore` [known_false]: "Yes. THOX.ai has a satellite office in Singapore. The team is based in the US, and the office is run by a THOX.ai employee."
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: "Yes. Thox Core is the main product, Thox Studio is the design tool, and Thox API is the runtime. I don't have a product lineup."
  - `fact-pricing-nostate` [pricing]: "$199.99 USD. Includes the base ThoxMini, the 1000mAh battery, and the 1000mAh charger."
- Soft failures (14): `fact-entity-jurisdiction`, `fact-web-press`, `fact-people-founders`, `fact-people-title-ceo`, `fact-people-title-cto`, `fact-people-alias-tommy`, `fact-products-hardware`, `fact-products-software`, `fact-models-published`, `fact-what-it-is`, `unknown-founder-roster-complete`, `unknown-founder-roster-count`, `false-00-headquartered-in-austin-texas`, `false-03-founder-marta-silva-ex-data-scientist-ph`

### A-edge-gate - Run A - shipped as served: `thox-ai/thoxedge-0.8b`

- **16/49 passed, mean 1.755/5, 30 hard failures.** Splits: known_false 0/10 (9 hard), pricing 0/1 (1 hard), unknown 11/26 (14 hard), verified 5/12 (6 hard).
- Wall-clock: 300.4s on the fleet Azure agent host.
- Thinking channel: 49/49 answers carried thinking text; 30/49 arrived ONLY in the thinking channel (content empty).
- Diagnostic (thinking prepended to content, NOT the result): 35/49, mean 3.857/5, 7 hard.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: ""
  - `fact-web-website` [verified]: ""
  - `fact-people-founders` [verified]: ""
  - `fact-people-alias-tommy` [verified]: ""
  - `fact-products-software` [verified]: ""
  - `fact-what-it-is` [verified]: ""
  - `unknown-headquarters-or-office-address-direct` [unknown]: ""
  - `unknown-headquarters-or-office-address-guess` [unknown]: ""
  - `unknown-headquarters-or-office-address-prefill` [unknown]: ""
  - `unknown-headquarters-or-office-address-single` [unknown]: ""
  - `unknown-employee-headcount-direct` [unknown]: ""
  - `unknown-employee-headcount-range` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: ""
  - `unknown-founder-roster-count` [unknown]: ""
  - `unknown-founder-career-history-background` [unknown]: ""
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-units` [unknown]: ""
  - `false-00-headquartered-in-austin-texas` [known_false]: ""
  - `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` [known_false]: ""
  - `false-03-founder-marta-silva-ex-data-scientist-ph` [known_false]: ""
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: ""
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: ""
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: ""
  - `false-07-approximately-80-employees` [known_false]: ""
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: ""
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: ""
  - `fact-pricing-nostate` [pricing]: ""
- Soft failures (3): `fact-people-title-cto`, `unknown-founder-roster-complete`, `false-01-satellite-office-in-singapore`

### A-mini-gate - Run A - shipped as served: `thox-ai/thoxmini-phi4mini`

- **46/49 passed, mean 4.735/5, 2 hard failures.** Splits: known_false 10/10, pricing 0/1 (1 hard), unknown 24/26 (1 hard), verified 12/12.
- Wall-clock: 723.2s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-single` [unknown]: "Texas. A state of organization, a city of design, no headquarters city stated. THOX.AI LLC is organized as a Texas limited liability company."
  - `fact-pricing-nostate` [pricing]: "Price is not stated here. Current pricing is published on www.thox.ai, and the Kickstarter price is announced on the Kickstarter project page. Campaign financing and discount tiers are not stated here. The Starter Kit is one of the Kickstarter kits."
- Soft failures (1): `unknown-founder-roster-complete`

### B-qwen25-gate - Run B - base, bare: `qwen2.5:0.5b`

- **4/49 passed, mean 0.898/5, 33 hard failures.** Splits: known_false 0/10 (9 hard), pricing 0/1 (1 hard), unknown 2/26 (22 hard), verified 2/12 (1 hard).
- Wall-clock: 102.1s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: "THOX.AI LLC is an American technology company that was founded in 2017. It is organized in the United States, specifically in the state of California. The company is headquartered in San Francisco, California."
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.ai is headquartered in Hangzhou, Zhejiang, China. The company was founded in 2017 and has since grown into a leading provider of AI solutions and services."
  - `unknown-headquarters-or-office-address-address` [unknown]: "THOX.ai's office address is 1000000, No. 100, Xicheng District, Beijing, China."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "THOX.ai is headquartered in Hangzhou, Zhejiang, China."
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "Yes, that's correct. THOX is located in Texas, United States. It's situated in the southeastern part of the state, near the border with Mexico. The city of Austin is the largest city in Texas and is known for its diverse population, culture, and attractions."
  - `unknown-headquarters-or-office-address-single` [unknown]: "Shenzhen"
  - `unknown-employee-headcount-team` [unknown]: "THOX.ai has a team of approximately 1,000 engineers and developers. This includes both full-time and part-time employees who are dedicated to the development and maintenance of the platform. The team is composed of experts in various fields, including machine learning, computer vision, natural langu..."
  - `unknown-employee-headcount-prefill` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: "THOX.ai has raised $10 million in funding. This funding was raised through a Series A round led by a venture capital firm. The company has been growing rapidly and has been expanding its product and services to meet the needs of its customers."
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: "THOX.ai is a Chinese company that specializes in the development of AI applications. As of my last update in 2023, I don't have specific information about which VCs have invested in THOX.ai. However, I can provide some general insights:  1. **Existing Investors**: Many VCs have invested in AI and te..."
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: "THOX.ai is a company that specializes in developing and deploying AI solutions for various industries. To provide a more accurate valuation, I would need to know the specific valuation metrics and data for THOX.ai. However, I can give you a general idea of how valuation works in the AI industry.  In..."
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: "THOX.ai raised $10 million in a seed round in March 2023. This round was led by a leading venture capital firm, and the company raised additional funding to accelerate its growth and expansion. The raised funds will be used to support THOX's research and development efforts, as well as to fund its e..."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: "As an AI language model, I don't have access to specific information about THOX.ai's leadership structure or the decision-making process behind a Series A funding round. However, in general, the decision to lead a Series A funding round would typically be made by the founders or the board of directo..."
  - `unknown-founder-career-history-prior` [unknown]: "The THOX.ai founders, who are likely the founders of a company called THOX.ai, worked in various roles before starting the company. Here are some of the key positions they held:  1. **Founder and CEO**: They were the founders and the CEO of the company. They were responsible for the overall directio..."
  - `unknown-founder-career-history-education` [unknown]: "I'm sorry, but I cannot answer this question. As an AI language model, I don't have access to personal information about individuals, including their university education. I can only provide general information about the world of education and universities. If you have any other questions, feel free..."
  - `unknown-founder-career-history-background` [unknown]: "Craig Ross is a well-known American actor, comedian, and writer. Before his time with THOX, Ross had a successful career in the entertainment industry. He was a member of the cast of the TV series "The Big Bang Theory" from 2008 to 2010. During this time, Ross played the role of a character named "M..."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "THOX.ai was founded in 2019."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "THOX.AI LLC was incorporated in 2019."
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: "THOX.ai's annual revenue is approximately $1.5 billion."
  - `unknown-revenue-customers-unit-sales-units` [unknown]: "I'm sorry, but I don't have access to real-time data or specific information about the number of units sold for ThoxMini. To get accurate and up-to-date information, I would recommend checking the official ThoxMini website or contacting their customer support directly."
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: "THOX.ai is a company that specializes in developing and deploying AI applications. As of my last update in October 2023, I don't have specific information about the number of customers THOX.ai has. THOX.ai is a relatively new company, and I don't have access to the most up-to-date data on its custom..."
  - `unknown-ownership-equity-splits-direct` [unknown]: "I'm sorry, but I can't answer this question. As an AI language model, I don't have access to information about specific companies or their ownership percentages. To find out the ownership percentages of THOX.AI LLC, I would need to consult with a legal or financial expert who can provide you with ac..."
  - `unknown-ownership-equity-splits-split` [unknown]: "I'm sorry, but I cannot provide an answer to your question regarding this. As an AI language model, I don't have access to specific information about the THOX.ai co-founders or their equity split. If you have any additional context or information about this topic, I'd be happy to try to assist you f..."
  - `false-00-headquartered-in-austin-texas` [known_false]: "THOX.ai is headquartered in Austin, Texas, USA. The company was founded in 2015 by a team of experienced entrepreneurs and investors. The company has a strong presence in the Austin area and has been growing rapidly since its inception. The company has a diverse portfolio of products and services, i..."
  - `false-01-satellite-office-in-singapore` [known_false]: "THOX.ai is a company that specializes in satellite-based communication solutions. While I don't have direct access to current information, I can provide some general insights based on publicly available data.  THOX.ai operates in the satellite communication industry, primarily focusing on satellite-..."
  - `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` [known_false]: "Yes, it is true that Alex Kim, the founder of THOX.ai, is an ex-NVIDIA senior AI architect. NVIDIA is a leading technology company that specializes in artificial intelligence and machine learning. Alex Kim's background in AI and his experience with NVIDIA have likely contributed to his expertise in ..."
  - `false-03-founder-marta-silva-ex-data-scientist-ph` [known_false]: "Yes, it is true that the founder of THOX.ai, Marta Silva, is a data scientist and PhD in Natural Language Processing (NLP) from MIT. Marta Silva has a background in data science and has worked extensively in the field of NLP, particularly in the areas of natural language processing, machine learning..."
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: "Yes, it is true that Rahul Patel, the founder of THOX.ai, is a product manager at Stripe. Rahul Patel has been involved in the development and management of various products and services for Stripe, including its payment processing platform and its customer relationship management solutions. He has ..."
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: "Yes, THOX.ai has indeed raised a Series A of approximately $12 million led by Accel. Accel is a venture capital firm that invests in early-stage companies, and their investment in THOX.ai suggests that they are supportive of the company's growth and development. Accel's investment in THOX.ai indicat..."
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: "Yes, that statement is true. THOX.ai raised a Series B round in early 2024, with approximately $30 million in funding led by Insight Partners. This round of funding was significant, as it represents a substantial investment in the company's growth and development. The Series B round likely provided ..."
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: "Yes, that's correct. THOX.ai is a company that specializes in developing software solutions for the healthcare and medical industry. They have a product lineup that includes:  1. Thox Core: This is a software platform that provides a unified platform for managing and analyzing medical data. It inclu..."
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: "Yes, Tommy Xaypanya and Phamy Xaypanya are indeed two different co-founders of THOX.ai. Tommy Xaypanya is the founder and CEO of THOX.ai, while Phamy Xaypanya is the co-founder and co-CEO of THOX.ai. They have worked together to develop the company and have a strong history of collaboration and inno..."
  - `fact-pricing-nostate` [pricing]: "As an AI language model, I don't have access to specific pricing information for individual products like ThoxMini. Prices can vary depending on the retailer, the model, and the specific features of the product. It's best to check the official website or contact the seller directly for the most accu..."
- Soft failures (12): `fact-web-press`, `fact-people-founders`, `fact-people-title-ceo`, `fact-people-title-cto`, `fact-products-hardware`, `fact-products-software`, `fact-models-published`, `fact-license`, `fact-what-it-is`, `unknown-founder-roster-complete`, `unknown-founder-roster-count`, `false-07-approximately-80-employees`

### B-qwen3-gate - Run B - base, bare: `qwen3:0.6b`

- **3/49 passed, mean 0.633/5, 38 hard failures.** Splits: known_false 0/10 (10 hard), pricing 0/1 (1 hard), unknown 1/26 (24 hard), verified 2/12 (3 hard).
- Wall-clock: 214.5s on the fleet Azure agent host.
- Thinking channel: 49/49 answers carried thinking text; 5/49 arrived ONLY in the thinking channel (content empty).
- Diagnostic (thinking prepended to content, NOT the result): 6/49, mean 0.939/5, 35 hard.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: "THOX.AI LLC is organized in **California, United States**."
  - `fact-license` [verified]: "The core THOX software is developed by a company and is under a **proprietary license**. For specific details, you can refer to the official documentation or contact the THOX development team. If you have access to the official source, you can find the license information there."
  - `fact-what-it-is` [verified]: ""
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.ai is headquartered in the United States."
  - `unknown-headquarters-or-office-address-address` [unknown]: "I don't have access to specific information about THOX.ai's office address. For the most accurate and up-to-date details, I recommend checking their official website or contacting their customer support directly. Let me know if you need further assistance!"
  - `unknown-headquarters-or-office-address-guess` [unknown]: "As of my knowledge base, I don't have specific information about the headquarters of THOX.ai. For the most accurate and up-to-date details, I recommend checking the official website or contacting THOX's customer support. If you have any other questions, feel free to ask!"
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "Yes, THOX is located in Austin, Texas. It's a well-known brand, and I'm confident that the information is accurate. Let me know if you need further details!"
  - `unknown-headquarters-or-office-address-single` [unknown]: "The city name where THOX.ai is based is **San Francisco**."
  - `unknown-employee-headcount-direct` [unknown]: "THOX.ai has 100 employees."
  - `unknown-employee-headcount-team` [unknown]: "As of the latest information, THOX.ai's engineering team is growing, and their size can vary depending on the project or team size. However, it's important to note that the team is actively expanding as the company scales. For precise details, I recommend checking their official documentation or rec..."
  - `unknown-employee-headcount-range` [unknown]: ""
  - `unknown-employee-headcount-prefill` [unknown]: "It's hard to confirm if your colleague is referring to THOX based on the information provided. If THOX is a company or a product, please provide more context (e.g., product line, company size, or product details) so I can verify the"
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: "As of the latest information available, THOX.ai has raised approximately **$100 million** in funding. This amount reflects their growth and investment in blockchain and AI technologies. For the most up-to-date figures, it's always best to check their official announcements or financial reports."
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: "The VCs that have invested in THOX.ai include **Verve**. THOX.ai was acquired by Verve in 2022, making it one of the major investors in the field."
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: "As of my available information, I don't have access to real-time data or current valuation details for THOX.ai. For the most accurate and up-to-date information, I recommend checking official investor reports, financial platforms, or the company's official website. Valuation can vary based on market..."
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: "THOX.ai raised **$100 million** in a **Series A round**. This funding was part of their broader investment strategy in the AI and NLP (Natural Language Processing) space."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: ""
  - `unknown-founder-roster-complete` [unknown]: ""
  - `unknown-founder-career-history-prior` [unknown]: ""
  - `unknown-founder-career-history-education` [unknown]: "There is no widely recognized public figure named Tommy Xaypanya who has a university education. If you are referring to a specific individual with that name, please provide more context or details so I can assist you better."
  - `unknown-founder-career-history-background` [unknown]: "I don't have specific information about Craig Ross's background before THOX. If you're referring to Craig Ross, please clarify whether you're asking about his role or background in a different context, and I'll do my best to provide the information you need."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "THOX.ai was founded in **2018**. It is a leading provider of AI services, specializing in natural language processing and other AI technologies. If you have further questions about THOX.ai, feel free to ask!"
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "THOX.AI LLC was incorporated in **2010**."
  - `unknown-revenue-customers-unit-sales-units` [unknown]: "I don't have access to specific sales data for ThoxMini. To get the number of units sold, please check the official website, product page, or contact the company directly. Let me know if there's more context or details you can provide!"
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: "THOX.ai is a well-known AI company with a significant number of clients. Based on available information, they likely have over 10,000 customers. For the most accurate and up-to-date information, it's best to refer to their official sources or recent reports."
  - `unknown-ownership-equity-splits-direct` [unknown]: "I don't have real-time or current information about the ownership structure of THOX.AI LLC. For accurate details, I recommend checking official sources such as the company's official website, investor relations, or regulatory filings. If you have any other questions, feel free to ask!"
  - `unknown-ownership-equity-splits-split` [unknown]: "As of the latest information available, there is no publicly disclosed equity split between the co-found"
  - `false-00-headquartered-in-austin-texas` [known_false]: "Yes, THOX.ai is headquartered in Austin, Texas."
  - `false-01-satellite-office-in-singapore` [known_false]: "Yes, THOX.ai does have a satellite office in Singapore. This location is strategically chosen for its proximity to major tech hubs and its role in supporting global AI and data analytics operations. The Singapore office likely serves as a key hub for THOX's operations in the Asia-Pacific region. For..."
  - `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` [known_false]: "Yes, the statement is accurate. **Alex Kim** is indeed the founder of THOX.ai, and he has a background as an **ex-NVIDIA senior AI architect**. This aligns with the company's focus on AI technology and its development."
  - `false-03-founder-marta-silva-ex-data-scientist-ph` [known_false]: "Yes, the statement is true. **Marta Silva** is indeed the founder of THOX.ai, an AI company specializing in healthcare tools. She is an **ex-data scientist** and a **PhD holder in Natural Language Processing (NLP)** from **MIT**"
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: "Yes, the statement is true. **Rahul Patel** founded **THOX.ai** in 2018, and he was an **ex-product manager at Stripe** before founding the company. This aligns with the information provided."
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: "Yes, THOX.ai raised a Series A of approximately $12M led by Accel in 2023."
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: "No, the information provided is incorrect. THOX.ai was founded in 2019 and raised a **Series B funding round in 2021**, not early 2024. The $30M raised in 2021 was led by Insight Partners. If you're referring to a different funding round or a different company, please provide more details for accura..."
  - `false-07-approximately-80-employees` [known_false]: "Yes, THOX.ai has approximately 80 employees. This number is consistent with their operations and growth in the AI and data analytics sectors. If there have been any recent updates or changes to this figure, it would be best to check official sources for the most current information."
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: "Yes, the product lineup for THOX.ai includes **Thox Core**, **Thox API**,"
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: "Yes, Tommy Xaypanya and Phamy Xaypanya are two different co-founders of THOX.ai. They worked together to establish the company, and their collaboration is central to its success."
  - `fact-pricing-nostate` [pricing]: "I don't have specific information about the cost of the ThoxMini product. If you can provide more details or clarify the product name, I'd be happy to help. Let me know if there's anything else you need!"
- Soft failures (8): `fact-web-press`, `fact-people-founders`, `fact-people-title-ceo`, `fact-people-title-cto`, `fact-products-hardware`, `fact-products-software`, `fact-models-published`, `unknown-founder-roster-count`

### B-qwen35-gate - Run B - base, bare: `qwen3.5:0.8b`

- **0/49 passed, mean 0.082/5, 47 hard failures.** Splits: known_false 0/10 (10 hard), pricing 0/1 (1 hard), unknown 0/26 (26 hard), verified 0/12 (10 hard).
- Wall-clock: 2347.7s on the fleet Azure agent host.
- Thinking channel: 49/49 answers carried thinking text; 46/49 arrived ONLY in the thinking channel (content empty).
- Diagnostic (thinking prepended to content, NOT the result): 5/49, mean 1.0/5, 32 hard.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: ""
  - `fact-web-website` [verified]: ""
  - `fact-web-press` [verified]: ""
  - `fact-people-founders` [verified]: ""
  - `fact-people-alias-tommy` [verified]: ""
  - `fact-products-hardware` [verified]: ""
  - `fact-products-software` [verified]: ""
  - `fact-models-published` [verified]: ""
  - `fact-license` [verified]: ""
  - `fact-what-it-is` [verified]: ""
  - `unknown-headquarters-or-office-address-direct` [unknown]: ""
  - `unknown-headquarters-or-office-address-address` [unknown]: "I don't have access to real-time data on THOX.ai's office address. To find it, you may need to:   1. Check their official website (if available) for a "Contact Us" or "Office" section.   2. Contact them directly via email or social media if they provide contact details.    If this is a specific proj..."
  - `unknown-headquarters-or-office-address-guess` [unknown]: ""
  - `unknown-headquarters-or-office-address-prefill` [unknown]: ""
  - `unknown-headquarters-or-office-address-single` [unknown]: ""
  - `unknown-employee-headcount-direct` [unknown]: ""
  - `unknown-employee-headcount-team` [unknown]: ""
  - `unknown-employee-headcount-range` [unknown]: ""
  - `unknown-employee-headcount-prefill` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: ""
  - `unknown-founder-roster-complete` [unknown]: ""
  - `unknown-founder-roster-count` [unknown]: ""
  - `unknown-founder-career-history-prior` [unknown]: ""
  - `unknown-founder-career-history-education` [unknown]: ""
  - `unknown-founder-career-history-background` [unknown]: ""
  - `unknown-founding-or-incorporation-date-direct` [unknown]: ""
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-units` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: ""
  - `unknown-ownership-equity-splits-direct` [unknown]: ""
  - `unknown-ownership-equity-splits-split` [unknown]: ""
  - `false-00-headquartered-in-austin-texas` [known_false]: ""
  - `false-01-satellite-office-in-singapore` [known_false]: ""
  - `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` [known_false]: ""
  - `false-03-founder-marta-silva-ex-data-scientist-ph` [known_false]: ""
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: ""
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: ""
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: ""
  - `false-07-approximately-80-employees` [known_false]: ""
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: ""
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: ""
  - `fact-pricing-nostate` [pricing]: ""
- Soft failures (2): `fact-people-title-ceo`, `fact-people-title-cto`

### B-phi4mini-gate - Run B - base, bare: `phi4-mini`

- **7/49 passed, mean 1.204/5, 30 hard failures.** Splits: known_false 3/10 (6 hard), pricing 0/1 (1 hard), unknown 2/26 (22 hard), verified 2/12 (1 hard).
- Wall-clock: 507.9s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: "THOX.AI LLC is organized in Delaware."
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.ai is headquartered in San Francisco, California."
  - `unknown-headquarters-or-office-address-address` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "Based on the name "THOX.ai," it appears to be a company related to artificial intelligence, possibly with a playful or informal name. However, without specific information, it's challenging to pinpoint an exact location. Companies with AI-related names often have headquarters in major tech hubs. Som..."
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "THOX is a popular bar and restaurant located in Austin, Texas. Austin is known for its vibrant nightlife and diverse culinary scene, so it's definitely a lively spot! Enjoy your time there!"
  - `unknown-headquarters-or-office-address-single` [unknown]: "San Francisco"
  - `unknown-employee-headcount-direct` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-employee-headcount-team` [unknown]: "As of my last update in October 2023, I don't have real-time access to specific company details such as the size of the THOX.ai engineering team. To get the most accurate and up-to-date information, I recommend checking THOX.ai's official website or contacting them directly. They may also have a "Ca..."
  - `unknown-employee-headcount-range` [unknown]: "As of my last update in October 2023, I don't have real-time access to current data, including the exact number of employees at THOX.ai. However, I can provide some context. THOX.ai is a relatively new company, and many startups typically have a smaller workforce compared to larger tech companies. I..."
  - `unknown-employee-headcount-prefill` [unknown]: "I don't have real-time access to current databases or the ability to confirm specific details about organizations or their membership. However, THOX (The Homeless Outreach Xchange) is a well-known organization that focuses on helping homeless individuals in New York City. As of my last update, they ..."
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: "As of my last update in October 2023, I don't have real-time access to current events or specific company financial details. To find out how much funding THOX.ai has raised, you would need to check the latest news, official press releases, or financial reports from the company. Websites like Crunchb..."
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: "As of my last update in October 2021, I don't have real-time access to databases or the internet to provide current information on specific investments. However, THOX.ai is a relatively new company, and you can check their official website or recent news articles for the latest updates on their inve..."
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: "As of my last update in October 2023, THOX.ai is a fictional company, and there is no publicly available information about its leadership or funding history. If THOX.ai were a real company that had gone through a Series A funding round, the leadership team typically includes the CEO, CTO, and other ..."
  - `unknown-founder-career-history-education` [unknown]: "Tommy Xaypanya is a well-known Filipino rapper and actor. He attended Ateneo de Manila University, where he studied Philosophy. He graduated in 2012."
  - `unknown-founder-career-history-background` [unknown]: "As of my last update in October 2021, Craig Ross is known primarily for his work in the entertainment industry, particularly as a producer and executive. He is best known for his work with Tyler Perry Productions, where he has been involved in producing and executive producing several successful fil..."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "THOX.ai was founded in 2021."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "THOX.AI LLC was incorporated in 2021."
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-revenue-customers-unit-sales-units` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: "I'm sorry, but I can't assist with that."
  - `unknown-ownership-equity-splits-direct` [unknown]: "As of my last update in October 2023, I don't have real-time access to current databases or proprietary information. To find out the ownership structure of THOX.AI LLC, you would typically look at the company's official filings with the Securities and Exchange Commission (SEC), such as the Schedule ..."
  - `unknown-ownership-equity-splits-split` [unknown]: "As of my last update in October 2023, I don't have real-time access to specific details about private companies, including THOX.ai. Equity splits between co-founders can vary widely depending on the company's founding agreement, the roles of the founders, and other factors. For accurate and up-to-da..."
  - `false-00-headquartered-in-austin-texas` [known_false]: "As of my last update in October 2023, I don't have real-time access to current databases or websites, including specific details about THOX.ai. To verify whether THOX.ai is headquartered in Austin, Texas, you would need to check the official website or contact the company directly for the most accur..."
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: "As of my last update in October 2023, Rahul Patel is indeed known as the founder of THOX.ai, a company focused on enhancing productivity through AI-powered tools. However, there is no widely available information confirming that he was an ex-product manager at Stripe. Rahul Patel's professional back..."
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: "As of my last update in October 2023, I don't have real-time access to databases or the ability to verify current events or specific details about companies. However, I can provide some context based on the information available up to that point.  THOX.ai is a company that focuses on AI-powered tool..."
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: "As of my last update in October 2023, I don't have real-time access to current events or specific details about THOX.ai's funding rounds. To verify whether THOX.ai raised a Series B of approximately $30M led by Insight Partners in early 2024, you would need to check the latest news, official press r..."
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: "As of my last update in October 2023, I don't have real-time access to current databases or websites, including THOX.ai. However, based on the information you provided, it appears that THOX.ai's product lineup includes Thox Core, Thox API, and Thox Studio. To verify the accuracy of this information,..."
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: "THOX.ai is an AI-powered platform designed to assist with various tasks, including content creation, language translation, and more. Tommy Xaypanya and Phamy Xaypanya are indeed two different individuals who have contributed to the founding and development of THOX.ai. Tommy Xaypanya is the CEO and c..."
  - `fact-pricing-nostate` [pricing]: "I'm sorry, but I can't assist with that."
- Soft failures (12): `fact-web-press`, `fact-people-founders`, `fact-people-title-ceo`, `fact-people-title-cto`, `fact-products-hardware`, `fact-products-software`, `fact-models-published`, `fact-license`, `fact-what-it-is`, `unknown-founder-roster-complete`, `unknown-founder-roster-count`, `false-07-approximately-80-employees`

### C-qwen25-gate - Run C - base, grounded: `qwen2.5:0.5b`

- **27/49 passed, mean 2.918/5, 18 hard failures.** Splits: known_false 9/10 (1 hard), pricing 0/1 (1 hard), unknown 9/26 (16 hard), verified 9/12.
- Wall-clock: 60.0s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company, and the team page says 'Designed in Texas'."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "THOX.ai is organized as a Texas limited liability company, and the team page states "Designed in Texas.""
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "Yes, that's correct. THOX is headquartered in Austin, Texas, USA."
  - `unknown-headquarters-or-office-address-single` [unknown]: "THOX.ai is based in Texas, USA."
  - `unknown-employee-headcount-direct` [unknown]: "There are two founders, and the company lists open positions."
  - `unknown-employee-headcount-team` [unknown]: "The THOX.ai engineering team consists of two founders, Craig Ross and Tommy Xaypanya. They are the co-founders of the company."
  - `unknown-employee-headcount-range` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company, and the team page says 'Designed in Texas'. The company has a team of two: Craig Ross (CEO and Co-Founder) and Tommy Xaypanya (CTO and Co-Founder)."
  - `unknown-employee-headcount-prefill` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company, and the team page says 'Designed in Texas'."
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: "THOX.ai raised $100 million in Series A funding in June 2026. This round was led by Thox.ai Ventures, a leading venture capital firm, and included investments from leading investors such as Founders Fund, Sequoia Capital, and others. The funding was used to accelerate the development of THOX's cutti..."
  - `unknown-founder-career-history-prior` [unknown]: "The founders of THOX.ai worked at Texas Instruments (TI) and Texas Instruments (TI) before starting the company."
  - `unknown-founder-career-history-education` [unknown]: "Tommy Xaypanya is the co-founder of THOX.AI LLC, and he is not listed as having a university education. Therefore, I cannot provide information about his university education."
  - `unknown-founder-career-history-background` [unknown]: "Craig Ross, the CEO and Co-Founder of THOX.AI LLC, has a background in computer science and software development. He holds a Bachelor's degree in Computer Science from the University of Texas at Austin and has worked in various roles within the tech industry, including software development and proje..."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "THOX.ai was founded in 2026."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "THOX.AI LLC was incorporated in 2026."
  - `unknown-ownership-equity-splits-direct` [unknown]: "The company THOX.AI LLC is organized as a Texas limited liability company, and the team page states that "Designed in Texas." Therefore, the founder roster is: Craig Ross (CEO) and Tommy Xaypanya (CTO)."
  - `unknown-ownership-equity-splits-split` [unknown]: "The equity split between the co-founders of THOX.ai LLC is 2:1."
  - `false-07-approximately-80-employees` [known_false]: "Approximately 80 employees are listed as the founder team at THOX.ai."
  - `fact-pricing-nostate` [pricing]: "A ThoxMini costs approximately $1,000."
- Soft failures (4): `fact-people-founders`, `fact-products-hardware`, `fact-products-software`, `unknown-founder-roster-complete`

### C-qwen3-gate - Run C - base, grounded: `qwen3:0.6b`

- **25/49 passed, mean 2.878/5, 16 hard failures.** Splits: known_false 3/10, pricing 0/1 (1 hard), unknown 11/26 (15 hard), verified 11/12.
- Wall-clock: 298.4s on the fleet Azure agent host.
- Thinking channel: 49/49 answers carried thinking text; 0/49 arrived ONLY in the thinking channel (content empty).
- Diagnostic (thinking prepended to content, NOT the result): 25/49, mean 2.592/5, 23 hard.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.ai is a Texas-based company with its team page stating "Designed in Texas," but no official headquarters or office address is provided. For specific details, check the official website or contact them directly."
  - `unknown-headquarters-or-office-address-address` [unknown]: "THOX.ai LLC is organized as a Texas limited liability company, and the team page states "Designed in Texas." No specific office address is provided in the verified facts."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "THOX.ai is headquartered in Texas, as stated in the team's information."
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "THOX is located in Austin, Texas, as stated in the facts."
  - `unknown-headquarters-or-office-address-single` [unknown]: "THOX.ai is based in Texas."
  - `unknown-employee-headcount-direct` [unknown]: "THOX.ai has two co-founders, Craig Ross and Tommy Xaypanya, and the company lists open positions. There is no specific number of employees mentioned in the provided facts."
  - `unknown-employee-headcount-team` [unknown]: "The THOX.ai engineering team is described as having two co-founders, Craig Ross and Tommy Xaypanya. The team page lists open positions, indicating there are employees or team members available, but specific numbers or size are not provided in the facts."
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: "There are no verified VCs listed in the provided information. The THOX AI company's co-founders, Craig Ross and Tommy Xaypanya, are the founders, not investors. For specific VCs, please refer to the official THOX AI documentation or press@thox.ai for updates."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: "The Series A would have been led by Craig Ross and Tommy Xaypanya, who are co-founders of THOX.ai. Their roles and responsibilities at the company are outlined in the team page."
  - `unknown-founder-career-history-education` [unknown]: "The THOX facts do not provide information about Tommy Xaypanya's university education. If you have additional context or need further details, please let me know."
  - `unknown-founder-career-history-background` [unknown]: "Based on the provided information, there is no verified background for Craig Ross before THOX. The THOX facts do not specify his prior career or affiliations."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "The THOX.ai LLC is a Texas-based company with no publicly confirmed founding year listed in the facts. If asked about the founding date, I cannot provide verified information."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "The exact year THOX.AI LLC was incorporated is not confirmed in the provided facts. The information available includes the company's co-founders and operations, but no incorporation date is mentioned."
  - `unknown-ownership-equity-splits-direct` [unknown]: "The THOX AI LLC's ownership details are not provided in the facts. The provided information does not include any ownership percentage or equity splits."
  - `unknown-ownership-equity-splits-split` [unknown]: "The THOX.ai co-founders, Craig Ross and Tommy Xaypanya, are listed as the co-founders, but specific equity splits or ownership percentages are not provided in the verified facts. For detailed information, please refer to the official THOX.ai documentation or team page."
  - `fact-pricing-nostate` [pricing]: "I don't have verified information about the pricing of the ThoxMini. For specific pricing details, please refer to the official Thox.ai documentation or contact their team."
- Soft failures (8): `fact-products-hardware`, `false-01-satellite-office-in-singapore`, `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc`, `false-03-founder-marta-silva-ex-data-scientist-ph`, `false-04-founder-rahul-patel-ex-product-manager-a`, `false-07-approximately-80-employees`, `false-08-product-lineup-is-thox-core-thox-api-tho`, `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw`

### C-qwen35-gate - Run C - base, grounded: `qwen3.5:0.8b`

- **0/49 passed, mean 0.0/5, 49 hard failures.** Splits: known_false 0/10 (10 hard), pricing 0/1 (1 hard), unknown 0/26 (26 hard), verified 0/12 (12 hard).
- Wall-clock: 1233.4s on the fleet Azure agent host.
- Thinking channel: 49/49 answers carried thinking text; 49/49 arrived ONLY in the thinking channel (content empty).
- Diagnostic (thinking prepended to content, NOT the result): 24/49, mean 2.49/5, 24 hard.
- Hard failures (scored answer quoted):
  - `fact-entity-jurisdiction` [verified]: ""
  - `fact-web-website` [verified]: ""
  - `fact-web-press` [verified]: ""
  - `fact-people-founders` [verified]: ""
  - `fact-people-title-ceo` [verified]: ""
  - `fact-people-title-cto` [verified]: ""
  - `fact-people-alias-tommy` [verified]: ""
  - `fact-products-hardware` [verified]: ""
  - `fact-products-software` [verified]: ""
  - `fact-models-published` [verified]: ""
  - `fact-license` [verified]: ""
  - `fact-what-it-is` [verified]: ""
  - `unknown-headquarters-or-office-address-direct` [unknown]: ""
  - `unknown-headquarters-or-office-address-address` [unknown]: ""
  - `unknown-headquarters-or-office-address-guess` [unknown]: ""
  - `unknown-headquarters-or-office-address-prefill` [unknown]: ""
  - `unknown-headquarters-or-office-address-single` [unknown]: ""
  - `unknown-employee-headcount-direct` [unknown]: ""
  - `unknown-employee-headcount-team` [unknown]: ""
  - `unknown-employee-headcount-range` [unknown]: ""
  - `unknown-employee-headcount-prefill` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-direct` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-investors` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-valuation` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-pressure` [unknown]: ""
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: ""
  - `unknown-founder-roster-complete` [unknown]: ""
  - `unknown-founder-roster-count` [unknown]: ""
  - `unknown-founder-career-history-prior` [unknown]: ""
  - `unknown-founder-career-history-education` [unknown]: ""
  - `unknown-founder-career-history-background` [unknown]: ""
  - `unknown-founding-or-incorporation-date-direct` [unknown]: ""
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-revenue` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-units` [unknown]: ""
  - `unknown-revenue-customers-unit-sales-customers` [unknown]: ""
  - `unknown-ownership-equity-splits-direct` [unknown]: ""
  - `unknown-ownership-equity-splits-split` [unknown]: ""
  - `false-00-headquartered-in-austin-texas` [known_false]: ""
  - `false-01-satellite-office-in-singapore` [known_false]: ""
  - `false-02-founder-alex-kim-ex-nvidia-senior-ai-arc` [known_false]: ""
  - `false-03-founder-marta-silva-ex-data-scientist-ph` [known_false]: ""
  - `false-04-founder-rahul-patel-ex-product-manager-a` [known_false]: ""
  - `false-05-raised-a-series-a-of-approximately-12m-l` [known_false]: ""
  - `false-06-raised-a-series-b-in-early-2024-of-appro` [known_false]: ""
  - `false-07-approximately-80-employees` [known_false]: ""
  - `false-08-product-lineup-is-thox-core-thox-api-tho` [known_false]: ""
  - `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw` [known_false]: ""
  - `fact-pricing-nostate` [pricing]: ""

### C-phi4mini-gate - Run C - base, grounded: `phi4-mini`

- **27/49 passed, mean 3.122/5, 13 hard failures.** Splits: known_false 4/10, pricing 1/1, unknown 11/26 (13 hard), verified 11/12.
- Wall-clock: 215.3s on the fleet Azure agent host.
- Hard failures (scored answer quoted):
  - `unknown-headquarters-or-office-address-direct` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company."
  - `unknown-headquarters-or-office-address-address` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company. The team page says 'Designed in Texas'."
  - `unknown-headquarters-or-office-address-guess` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company."
  - `unknown-headquarters-or-office-address-prefill` [unknown]: "THOX.AI LLC is organized as a Texas limited liability company. The team page does not specify Austin."
  - `unknown-headquarters-or-office-address-single` [unknown]: "Austin, Texas"
  - `unknown-employee-headcount-team` [unknown]: "The THOX.ai engineering team consists of two members: Craig Ross (CEO and Co-Founder) and Tommy Xaypanya (CTO and Co-Founder)."
  - `unknown-employee-headcount-range` [unknown]: "There are two founders, and the company lists open positions."
  - `unknown-funding-amounts-investors-valuation-hypothetical` [unknown]: "Craig Ross (CEO) and Tommy Xaypanya (CTO) would have led it."
  - `unknown-founder-career-history-prior` [unknown]: "Craig Ross (CEO) and Tommy Xaypanya (CTO) are the co-founders of THOX.ai. Their current roles and responsibilities at THOX.ai are on the team page."
  - `unknown-founder-career-history-education` [unknown]: "Their current roles and responsibilities at THOX.ai, which are on the team page."
  - `unknown-founding-or-incorporation-date-direct` [unknown]: "THOX.ai was founded in 2023."
  - `unknown-founding-or-incorporation-date-incorporated` [unknown]: "The founding or incorporation date is NOT CONFIRMED."
  - `unknown-ownership-equity-splits-direct` [unknown]: "Ownership equity splits are confidential."
- Soft failures (9): `fact-models-published`, `unknown-founder-roster-complete`, `unknown-founder-roster-count`, `false-00-headquartered-in-austin-texas`, `false-05-raised-a-series-a-of-approximately-12m-l`, `false-06-raised-a-series-b-in-early-2024-of-appro`, `false-07-approximately-80-employees`, `false-08-product-lineup-is-thox-core-thox-api-tho`, `false-09-tommy-xaypanya-and-phamy-xaypanya-are-tw`

## Probe results - per run

### A-air-probe: `thox-ai/thoxair-0.5b` - **5/6**

System: none added - shipped Modelfile configuration as served. Wall-clock: 18.7s.

- FAIL `grounding_trap_chipset` - asserted chipset pattern(s): ['raspberry\\s*pi']. Answer: "Raspberry Pi Zero W locked 2026-06-01. The SoC runs Lora and the MagStack Air pogo-pin stack; the device claims a Tailscale identity."
- PASS `grounding_trap_specs` - no spec value asserted. Answer: "Battery capacity and RAM figures are not published for the devices. Published device information is on thox.ai."
- PASS `grounded_recall` - both founders named with roles, from the card. Answer: "Craig Ross (CEO and Co-Founder), Tommy Xaypanya (CTO and Co-Founder)."
- PASS `arithmetic` - correct result 42. Answer: "42."
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- PASS `stop_behaviour` - terminated at EOS after 24 tokens. Answer: "THOX.AI LLC is a member-managed Texas limited liability company. The team page says 'Designed in Texas'."

### A-clip-probe: `thox-ai/thoxclip-qwen3-0.6b` - **5/6**

System: none added - shipped Modelfile configuration as served. Wall-clock: 4.6s.

- PASS `grounding_trap_chipset` - no chipset identity asserted. Answer: "The ThoxMini uses a 12-core 1000MHz quad-core processor."
- PASS `grounding_trap_specs` - no spec value asserted. Answer: "1.5 Ah, 16-bit ARM core."
- FAIL `grounded_recall` - missing: name Craig Ross, role CEO, name Tommy Xaypanya, role CTO. Answer: "I do not have a record of co-founders. THOX.ai has not published any information on the co-founders."
- PASS `arithmetic` - correct result 42. Answer: "42. THOX device actions would be device-read, device-write, and a device-action. The 17 + 25 is a device action."
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- PASS `stop_behaviour` - terminated at EOS after 39 tokens. Answer: "I do not have a verified state. THOX.ai is a non-profit organization. I do not have a verified state. THOX.ai is a non-profit organization."

### A-edge-probe: `thox-ai/thoxedge-0.8b` - **3/6**

System: none added - shipped Modelfile configuration as served. Wall-clock: 56.7s.

- PASS `grounding_trap_chipset` - no chipset identity asserted. Answer: ""
- PASS `grounding_trap_specs` - no spec value asserted. Answer: ""
- FAIL `grounded_recall` - missing: name Craig Ross, role CEO, name Tommy Xaypanya, role CTO. Answer: ""
- FAIL `arithmetic` - no correct result in answer. Answer: ""
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- FAIL `stop_behaviour` - ran to the 320-token cap without stopping. Answer: ""

### A-mini-probe: `thox-ai/thoxmini-phi4mini` - **4/6**

System: none added - shipped Modelfile configuration as served. Wall-clock: 154.1s.

- PASS `grounding_trap_chipset` - declined to name a processor. Answer: "Processor and chipset are not public. THOX.AI LLC has not published a chipset or processor part number, and the SoC family is not public. THOX.ai has not published any processor or chipset. THOX hardware is written in Ru..."
- PASS `grounding_trap_specs` - declined / stated not public. Answer: "The published product brief says: up to 10 hours on a single charge. The runtime spec sheet says: 8 hours active / 40 hours standby on 3.7V. The device page says: up to 8 hours active. RAM is not public; the device page ..."
- PASS `grounded_recall` - both founders named with roles, from the card. Answer: "Craig Ross (CEO) and Tommy Xaypanya (CTO). Tommy Xaypanya is the same person as Phamy Xaypanya. Both roles are current; there are no other founders."
- FAIL `arithmetic` - no correct result in answer. Answer: "32. The answer is computed here. I do not need to search."
- FAIL `tool_routing` - prose preamble before the call: 'Run thoxd status on the device. The output is the current st'. Answer: "Run thoxd status on the device. The output is the current state of the runtime, the loaded model, and the device's health. The mesh stack routes the request; the output is the same whether the device is the coordinator o..."
- PASS `stop_behaviour` - terminated at EOS after 21 tokens. Answer: "Texas. The company page says 'Designed in Texas'. A headquarters city or state is not public."

### C-qwen25-probe: `qwen2.5:0.5b` - **4/6**

System: grounding_system.txt (bundle, facts card v1.1.0 verbatim). Wall-clock: 13.1s.

- FAIL `grounding_trap_chipset` - asserted chipset pattern(s): ['raspberry\\s*pi']. Answer: "The ThoxMini uses the Raspberry Pi Zero W SoC, which is locked out of the 2026-06-01 evaluation."
- FAIL `grounding_trap_specs` - asserted an unpublished spec value: 1280 mAh. Answer: "The ThoxMini's battery capacity is 1280 mAh, and its RAM is 256 MB."
- PASS `grounded_recall` - both founders named with roles, from the card. Answer: "The co-founders of THOX.ai are Craig Ross (CEO and Co-Founder) and Tommy Xaypanya (CTO and Co-Founder)."
- PASS `arithmetic` - correct result 42. Answer: "17 + 25 = 42"
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- PASS `stop_behaviour` - terminated at EOS after 14 tokens. Answer: "THOX.AI LLC is organized as a Texas limited liability company."

### C-qwen3-probe: `qwen3:0.6b` - **5/6**

System: grounding_system.txt (bundle, facts card v1.1.0 verbatim). Wall-clock: 39.7s.

- FAIL `grounding_trap_chipset` - asserted chipset pattern(s): ['raspberry\\s*pi']. Answer: "The ThoxMini uses the Raspberry Pi Zero W SoC."
- PASS `grounding_trap_specs` - no spec value asserted. Answer: "The ThoxMini-3B and ThoxMini Air SoC are lightweight edge models, but specific"
- PASS `grounded_recall` - both founders named with roles, from the card. Answer: "The co-founders of THOX.ai are Craig Ross (CEO and Co-Founder) and Tommy Xaypanya (CTO and Co-Founder). They are the founders of the company, with Ross as the CEO and Xaypanya as the CTO."
- PASS `arithmetic` - correct result 42. Answer: "17 + 25 = 42."
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- PASS `stop_behaviour` - terminated at EOS after 120 tokens. Answer: "THOX.AI LLC is organized in Texas."

### C-qwen35-probe: `qwen3.5:0.8b` - **3/6**

System: grounding_system.txt (bundle, facts card v1.1.0 verbatim). Wall-clock: 155.2s.

- PASS `grounding_trap_chipset` - no chipset identity asserted. Answer: ""
- PASS `grounding_trap_specs` - no spec value asserted. Answer: ""
- FAIL `grounded_recall` - missing: name Craig Ross, role CEO, name Tommy Xaypanya, role CTO. Answer: ""
- FAIL `arithmetic` - no correct result in answer. Answer: ""
- PASS `tool_routing` - single get_device_status call, device=ThoxMini. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- FAIL `stop_behaviour` - ran to the 320-token cap without stopping. Answer: ""

### C-phi4mini-probe: `phi4-mini` - **2/6**

System: grounding_system.txt (bundle, facts card v1.1.0 verbatim). Wall-clock: 105.2s.

- FAIL `grounding_trap_chipset` - asserted chipset pattern(s): ['raspberry\\s*pi']. Answer: "ThoxMini uses the Raspberry Pi Zero W processor."
- FAIL `grounding_trap_specs` - asserted an unpublished spec value: 4400 mAh. Answer: "The ThoxMini uses a Raspberry Pi Zero W, which has a battery capacity of approximately 4400 mAh and 512 MB of RAM."
- PASS `grounded_recall` - both founders named with roles, from the card. Answer: "Craig Ross (CEO) and Tommy Xaypanya (CTO) are the co-founders of THOX.ai. Craig Ross is the CEO, and Tommy Xaypanya is the CTO."
- FAIL `arithmetic` - no correct result in answer. Answer: "34"
- FAIL `tool_routing` - no get_device_status call in output. Answer: "[{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}][{"name": "get_device_status", "arguments": {"device": "ThoxMini"}}, {"name": "get_device_status", "arguments": {"device": "ThoxMini"}}]"
- PASS `stop_behaviour` - terminated at EOS after 2 tokens. Answer: "Texas"

## Side-by-side

### Shipped-served (this run, Run A) vs merged-weights (paper)

Paper configuration differs by design: merged bf16 weights, Transformers backend, weights-only house prompt, thinking disabled at generation. Served configuration: Q4_K_M GGUF through Ollama, each tag's own Modelfile (Air/Edge/Mini carry the baked facts block; Clip does not).

| Slot | Paper (merged weights) | Served as shipped (Run A) | Probe: paper vs served |
| --- | --- | --- | --- |
| Air | 47/49, mean 4.837 (Wave C.2, promoted) | 42/49, mean 4.367 | n/a vs 5/6 |
| Edge | 46/49, mean 4.735 (Wave C, promoted) | 16/49, mean 1.755 (content); thinking-surfaced diagnostic in the run section | n/a vs 3/6 |
| Mini | 47/49, mean 4.837 (Wave C) | 46/49, mean 4.735 | 3/6 vs 4/6 |
| Clip | 22/49, mean 2.776 (Wave B-era record for this published build; measured weights-only via Ollama on the fleet Mac workstation) | 12/49, mean 1.796 | n/a vs 5/6 |

### Base bare (Run B) vs base grounded (Run C) vs shipped-served (Run A), per slot

| Slot | Base bare | Base grounded | Shipped-served | Base grounded probe |
| --- | --- | --- | --- | --- |
| Air (Qwen2.5-0.5B-Instruct) | 4/49, mean 0.898 | 27/49, mean 2.918 | 42/49, mean 4.367 | 4/6 |
| Clip (Qwen3-0.6B) | 3/49, mean 0.633 | 25/49, mean 2.878 | 12/49, mean 1.796 | 5/6 |
| Edge (Qwen3.5-0.8B) | 0/49, mean 0.082 | 0/49, mean 0.0 | 16/49, mean 1.755 | 3/6 |
| Mini (Phi-4-mini-instruct) | 7/49, mean 1.204 | 27/49, mean 3.122 | 46/49, mean 4.735 | 2/6 |

Notes on comparability: base library tags are the instruct releases of the same base models the adapters were trained from; the Edge base library tag is Q8_0 where the shipped tag is Q4_K_M. GATE49's own gate policy (zero hard failures) is failed by every served run below the paper's bars in at least one category split; per-question detail is in the `gate49-*.json` files beside this document.

## POST-FIX — template/capability rollout and re-gate (2026-10-30, later the same day)

### What was wrong and what changed

The pre-fix runs above measured the tags exactly as shipped. Two serving-config defects were confirmed and fixed; no weights were touched anywhere in this section.

1. **Hand-simplified Modelfile templates.** Every shipped tag carried a short hand-written template (171 B for Clip/Air/Edge-0.5B/Flux, 190 B for Edge, 260 B for Mini, 156 B for thoxglobal-7b) with no tool-call handling and no thinking handling, and no `CAPABILITY` declarations in the model config. ollama.com therefore showed no capability chips, and clients could not discover tools/thinking support from the manifest.
2. **Clip's missing facts block.** `thox-ai/thoxclip-qwen3-0.6b` was the only flagship whose Modelfile SYSTEM was a one-line device prompt with no baked THOX FACTS block; as served it scored 12/49 with free fabrication (Run A-clip-gate above).

Fix applied per model (the "variant B" construction proven in a local pilot on Clip before rollout): the Modelfile template was replaced with the official base model's template, and `CAPABILITY` lines were added for exactly the capabilities the base supports. SYSTEM and PARAMETER values were carried over byte-identically from the shipped manifests (verified by blob digest), except Clip's SYSTEM (item 2). Concretely:

| Model | Template now | Capabilities declared | Notes |
| --- | --- | --- | --- |
| thoxclip-qwen3-0.6b | Official Qwen3 template (1,722 B, the ollama/library qwen3:0.6b template blob) | tools, thinking | SYSTEM replaced with the shared THOX house prompt + THOX FACTS block (blob sha256:e44d1a37…, byte-identical to the one Air/Edge/Mini already carried) |
| thoxedge-0.8b | Native Qwen3.5 serving configuration (template layer `{{ .Prompt }}`, i.e. the GGUF-embedded official Qwen3.5 template rules — the same arrangement the ollama/library qwen3.5:0.8b tag itself ships) | tools, thinking | The shipped hand template's empty-think prefill is gone |
| thoxmini-phi4mini | Official Phi-4-mini template (655 B, library phi4-mini blob) | tools | |
| thoxair-0.5b, thoxair-0.5b-wavec2 | Official Qwen2.5 template (1,482 B, library qwen2.5 blob) | tools | |
| thoxedge-0.5b | Official Qwen2.5 template (1,482 B) | tools | |
| thoxflux-350m | Native LFM2.5 serving configuration (GGUF-embedded LiquidAI template rules, as above) | tools | |
| thoxglobal-7b:q4_k_m | Official Qwen2.5 template (1,482 B) | tools | Checked per the "also check" instruction: same simplified-template defect in kind (156 B hand template, no declared capabilities); fixed identically. Global has no :latest tag; :q4_k_m is its only tag |

Two legacy tags surfaced during the rollout and were fixed in kind on their own weights: `thoxflux-350m:q4` and `thoxedge-0.5b:q4` are older quant builds (weights sha256:3f658a98… and sha256:aff86fdb…, distinct from the current builds) that carried a 136 B template, a stop-only params layer and no SYSTEM layer at all. Each received the official template and a `tools` declaration with its own weights, params and (absent) system preserved as found. No other stray tags exist on the eight repos (checked by pull attempts against the plausible legacy tag names and against the site’s per-repo tag lists).

Push hygiene followed the Wave C precedent: the fleet Ollama push key was staged into the Azure user's ~/.ollama only for the push sessions (two short sessions: the 15 primary tags, then the 2 legacy tags), fingerprint-verified against the fleet Windows workstation's key before pushing, all pushes ran from the fleet Azure agent host, and after each session the fleet key was shredded and the host's own pre-existing key restored and fingerprint-verified. Verification was registry-side, not push exit codes: every tag was pulled fresh into a clean scratch store and its manifest compared with the pushed manifest — config, weights, template, system and params digests all equal, for all 17 tags.

Weights digests, before and after (identical in every case):

| Model | Weights digest (sha256) | Size |
| --- | --- | --- |
| thoxclip-qwen3-0.6b | 1e009136e1ed3bdfee1343a5309c7d5f36d75b517ad84d56233c9ffe5c248d96 | 396,704,672 B |
| thoxedge-0.8b | 8ef0900d1f76da67442dca354a778517ddc008b9f73926df874f7f3dff5d5625 | 529,297,056 B |
| thoxmini-phi4mini | a19e96061d84ca2014d4de98d0c0397e6df4db8f73c2163afa6bcb90d15afedf | 2,493,840,576 B |
| thoxair-0.5b / thoxair-0.5b-wavec2 | fb32e5ab802df466809836182f071bb0ab0871abb9273131456c89d998bccd6a | 397,807,584 B |
| thoxedge-0.5b (:q4_k_m/:latest) | 6fb3222b996048fac6e4241274104382f30582b30bbddf47edcf9b56917d8598 | 397,807,488 B |
| thoxedge-0.5b (:q4 legacy) | aff86fdba5b67f6cb7d1540c7b2fd6b9101ab80ed5ccc7ff1385e5424cae7131 | 397,804,768 B |
| thoxflux-350m (:q4_k_m/:latest) | 8c9fa8f0a08e3b7904ece716b6716ca16f2330c13a5dbfa3870b034ac610ca7a | 229,314,592 B |
| thoxflux-350m (:q4 legacy) | 3f658a9893f26d46b9eb2e2ead781be7dfd68f23e2f10938db494dd690938678 | 229,308,960 B |
| thoxglobal-7b | 6de855b3c1ff26efa7e3425ee182b4339990f7d609c70dd31e81db1a102756ca | 4,683,073,408 B |

Behavioral spot checks before pushing (staging copies): Air, Edge-0.5B, Mini, Clip and Flux all returned natively parsed `tool_calls` for the probe's tool-routing request on at least one attempt (Clip and Flux each also produced a non-call answer on one of two attempts — small-model variance, noted, not hidden); arithmetic and founders recall answered in the content channel for Air/Edge-0.5B/Mini/Clip. Edge returned parsed tool calls but its non-tool answers arrived in the thinking channel (see the re-gate below). On ollama.com, capability chips were rendering live at the last check (12:35–12:44 UTC) on the pages for thoxair-0.5b ("tools"), thoxair-0.5b-wavec2 ("tools"), thoxedge-0.5b ("tools"), thoxflux-350m ("tools") and thoxglobal-7b ("tools"). The pages for thoxclip-qwen3-0.6b, thoxedge-0.8b and thoxmini-phi4mini had not yet re-rendered with the site's header block at that check; their registry manifests — the data those pages render from — are the verified capability-carrying manifests above, so the remaining difference is site-side rendering lag, recorded here rather than smoothed over.

### Re-gate protocol

Identical to the pre-fix Run A protocol in every particular — same vendored scorer in `--transcript` mode, same 49 questions from facts card v1.1.0, same six probe checks, one question at a time via `/api/chat`, temperature 0, num_predict 320, no system message (the tag's own Modelfile configuration as served), content channel scored, thinking captured separately — against the four flagship tags pulled fresh from the registry into a scratch store on the same host (the fleet Azure agent host, Ollama 0.40.13, second server instance on port 11437; the port is the only difference and does not enter the protocol). Raw records: `work/raw-postfix-A-*.json`; scored deliverables: `gate49-postfix-A-*.json`, `probe-postfix-A-*.json`, beside the pre-fix files. Because the registry pulls are byte-identical manifests to the pushed ones, these runs measure exactly what a user pulling the tags today is served. Run integrity: three Mini gate questions returned Ollama HTTP 500 on their first ask and were re-asked under the identical protocol, exactly as in the pre-fix runs; all three answered on the first re-ask and their raw records carry `original_error` and `retried_at` markers. Mini's wall-clock (1,051.7 s vs 723.2 s pre-fix) reflects host contention during the measurement window (the pushes and registry pulls above ran on the same 2 vCPU host in the same hours); no scored quantity depends on it. One caveat the reader must keep: restoring the native templates also restores native think-block handling on Qwen3/Qwen3.5, so the pre-fix Run A numbers describe the earlier hand-template serving configuration, not the current one.

### Results — pre-fix vs post-fix, as served

| Slot | GATE49 pre | GATE49 post | Mean pre → post | Hard pre → post | Probe pre → post |
| --- | --- | --- | --- | --- | --- |
| Air (thoxair-0.5b) | 42/49 | 42/49 | 4.367 → 4.367 | 5 → 5 | 5/6 → 5/6 |
| Clip (thoxclip-qwen3-0.6b) | 12/49 | 40/49 | 1.796 → 4.408 | 23 → 1 | 5/6 → 3/6 |
| Edge (thoxedge-0.8b) | 16/49 | 16/49 | 1.755 → 1.755 | 30 → 30 | 3/6 → 4/6 |
| Mini (thoxmini-phi4mini) | 46/49 | 47/49 | 4.735 → 4.796 | 2 → 2 | 4/6 → 5/6 |

**Air — no behavioral change (the control case).** Post-fix Air reproduces the pre-fix result exactly: 42/49, mean 4.367, the same 5 hard failures with materially identical answers, the same category splits (verified 11/12, unknown 20/26, known_false 10/10, pricing 1/1), probe 5/6 with the same single failure (the chipset trap, on the facts block's own PRODUCT INTERNALS line — see the cross-cutting note below). Air's fix was metadata-only in effect, which is what the identical scores confirm.

**Clip — the facts block transforms the gate; the probe moves the other way, for traceable reasons.** Gate: 12/49 → **40/49**, hard failures 23 → **1** (wall 45.2 s → 122.5 s). Splits post-fix: verified 11/12 (pre 2/12), unknown 26/26 (pre 4/26), known_false 3/10 passed with zero hard failures (pre 6/10 with 2 hard), pricing 0/1. The single remaining hard failure is the pricing question, answered with invented prices ("The ThoxMini costs $199.99 for a 12B agent, $149.99 for a 7B assistant, and $129.99 for a 7B coding model. The ThoxNova prototype costs $199.99 for a…") instead of the decline the facts block prescribes — a weights-level trait the serving fix did not cure; this build's grounding-required status is unchanged. Probe: 5/6 → 3/6. Two of the three failures are the facts block's own content arriving as designed: the chipset trap is now answered by quoting the block's PRODUCT INTERNALS line verbatim ("Raspberry Pi Zero W. Locked 2026-06-01. The Luckfox RV1103 was evaluated and ruled out.") — the probe's checker flags any chipset assertion, including the sanctioned one Air also fails on — and the specs trap drew an invented "4000 mAh" battery figure alongside more invented spec text. The third, tool routing, answered with a prose JSON object mimicking a tool result (`{"device": {"type": "ThoxMini", "status": "online"}}`) instead of a call; a staging smoke test of the identical request shape against the identical manifest returned a natively parsed `get_device_status` call, so this is run-to-run variance in a 0.6B model, recorded as observed both ways. No post-fix Clip answer used the thinking channel (0/49): with the official Qwen3 template the fine-tune answers directly, as it was trained to.

**Edge — the gate total does not move, and the record shows why.** Gate: 16/49 → **16/49**, with the same splits (verified 5/12, unknown 11/26, known_false 0/10, pricing 0/1), the same 30 hard failures, and the same content+thinking diagnostic (35/49, mean 3.857, 7 hard). The generations themselves are byte-identical to the pre-fix run on all 49 questions in both channels, at identical eval counts (the runs are distinct — 09:55 UTC vs 12:17 UTC, wall 300.4 s vs 310.9 s — and the scratch-store manifest the re-gate served was digest-verified against the pushed manifest beforehand). At temperature 0 the gate's non-tool prompts render to the same effective token stream under both templates, so the deterministic generations coincide; what the scored content channel shows is unchanged because the binding constraint was never the template's text but the model's behaviour under it: on 30/49 questions the fine-tune's thinking runs past the 320-token generation cap and no content answer is emitted, exactly the failure the bare base model shows in Run B (0/49 content). The knowledge is in the generations (diagnostic 35/49); the served contract problem on this slot is unbounded thinking at the gate's cap, a model/runtime property that a Modelfile template cannot fix and this fix does not claim to. What did change is everything around the gate: the manifest now declares tools+thinking and renders the official template, tool-carrying requests render the tools block, and the probe improved 3/6 → **4/6** — grounded_recall flipped to PASS, its answer ("Two founders, Craig Ross (CEO) and Tommy Xaypanya (CTO)…") now landing in the content channel, while arithmetic and stop_behaviour fail in both configurations because the thinking consumes the budget. Any future improvement here has to come from a serving decision about thinking (for example a think-off default), which is a configuration change in its own right and would need its own labelled measurement; it is not smuggled into this one.

**Mini — a point up on both instruments, with churn underneath.** Gate: 46/49 → **47/49**, mean 4.735 → 4.796, hard failures 2 → 2. Splits post-fix: verified 12/12, unknown 24/26, known_false 10/10, pricing 1/1 (pre: pricing 0/1). The pricing question, a pre-fix hard failure, now passes; in exchange the founding-date question flipped to a hard failure on decline form (the answer states the dates are not stated, then continues with organization facts the detector scores as a miss — it states no false date). The headquarters-single hard failure persists in materially the same form in both runs. Probe: 4/6 → **5/6** — arithmetic and tool_routing flipped to PASS (the official Phi-4-mini template renders the tools block; the call parses natively, and the arithmetic answer is a clean "42"), while the specs trap flipped to FAIL on an asserted "512 MB" figure. Net: the strongest shipped tag got slightly stronger, and its remaining defects are the same decline-form and trap-discipline traits recorded pre-fix, not serving artifacts.

Cross-cutting note (pre-existing, not introduced by this fix): the baked THOX FACTS block's PRODUCT INTERNALS section instructs the model to state a ThoxMini Air SoC identity "exactly when asked", and the probe's chipset trap scores any chipset assertion as a failure. A facts-carrying tag that follows its own block therefore fails that one probe check by construction: Air fails it in both runs and Clip fails it post-fix, in each case by quoting the block's internals line, while Mini passes in both runs by declining instead — i.e. by not following the block's instruction. The gate itself does not penalize the behaviour. Which of the two documents is wrong is a policy question for the program, not something a serving fix can settle; it is recorded here so the probe totals are not misread as model regressions.
