# Cinda Shoe Scoring — Handoff Guide for New Sessions

> **Purpose:** This document tells a new Claude session exactly how to score running shoes for the Cinda database. Follow it precisely. The scoring quality depends on consistency with the 185 shoes already scored.
>
> **Read first:** `SHOE_SCORING_FRAMEWORK.md` (in project knowledge). It contains the lab-data-to-score mapping tables, calibration anchors, edge case rules, and the 14-step scoring checklist. This document supplements it with process, column schema, and hard-won lessons.

---

## 1. Column Schema (39 columns)

Every shoe must have ALL columns. No partial entries. Tab-separated values for Google Sheets paste.

**Column order (exact):**

```
shoe_id | brand | model | version | full_name | alias_code | is_daily_trainer | is_super_trainer | is_recovery_shoe | is_workout_shoe | is_race_shoe | is_trail_shoe | is_walking_shoe | cushion_softness_1to5 | bounce_1to5 | stability_1to5 | rocker_1to5 | ground_feel_1to5 | weight_feel_1to5 | weight_g | heel_drop_mm | has_plate | plate_tech_name | plate_material | fit_volume | toe_box | width_options | support_type | heel_geometry | surface | wet_grip | release_status | release_year | release_quarter | retail_price_category | why_it_feels_this_way | avoid_if | similar_to | notable_detail | common_issues | data_confidence
```

### Enum values (use exactly these strings):

| Column | Allowed values |
|--------|---------------|
| fit_volume | low / standard / high |
| toe_box | narrow / standard / roomy |
| width_options | "standard only" / "standard and wide" |
| support_type | neutral / stable_neutral / stability |
| heel_geometry | standard / aggressive_forefoot |
| surface | road / road/trail / trail |
| wet_grip | poor / average / good / excellent |
| release_status | "rare to find" / "available" / "not yet released" |
| retail_price_category | Budget / Core / Premium / Super-premium |
| data_confidence | lab / estimated / placeholder |
| plate_material | carbon / nylon / fiberglass / (empty if no plate) |

### Boolean fields: Use TRUE/FALSE (not true/false, not 1/0)

### shoe_id: Continue from the last ID in the spreadsheet. Format: shoe_0186, shoe_0187, etc.

---

## 2. Data Sources (Tiered System)

### Tier 1: RunRepeat Lab Reviews (data_confidence = "lab")

The gold standard. RunRepeat cuts shoes in half and measures everything with lab instruments.

**What to extract from a RunRepeat review:**
- Midsole softness (HA and/or AC)
- Energy return heel %
- Shock absorption heel (SA)
- Heel stack (mm) and forefoot stack (mm)
- Drop (mm) — use MEASURED, not brand-claimed
- Weight (g)
- Width/Fit (mm)
- Toebox width (mm)
- Toebox height (mm)
- Flexibility/Stiffness (N)
- Breathability (1-5)
- Torsional rigidity (1-5)
- Heel counter stiffness (1-5)
- Midsole width forefoot (mm) and heel (mm)
- Outsole durability (mm wear)
- Reflective elements (Yes/No)
- Tongue gusset type
- Heel tab type
- Price (£)

**How to use the lab data:**
1. Read the FULL editorial review first (don't skip to the table)
2. Use the lab-data-to-score mapping tables in `SHOE_SCORING_FRAMEWORK.md`
3. The editorial context matters — a shoe that measures "average" on paper can feel exceptional or terrible depending on geometry, foam layering, and upper

**Critical rule for text columns:** Do NOT include specific RunRepeat lab measurements in `why_it_feels_this_way`, `avoid_if`, `notable_detail`, or `common_issues`. Describe the FEEL consequence, not the number. Say "among the softest midsoles ever tested" not "10.0 HA durometer". The lab data informs the score; the text describes the experience.

### Tier 2: ChatGPT Deep Research + Editorial Sources (data_confidence = "estimated")

Used when RunRepeat hasn't reviewed the shoe yet. Sources in priority order:
1. Doctors of Running (lab-quality editorial, includes stack/weight/drop specs)
2. Believe in the Run (detailed multi-tester reviews)
3. Road Trail Run (comprehensive, includes comparisons)
4. Running Warehouse reviews
5. Brand specs (weight, stack, drop, foam name)
6. Supwell (good for Chinese brand shoes)

**Scoring confidence:** ±1 on feel scores. Flag as `data_confidence: estimated`. These upgrade to "lab" when RunRepeat publishes.

**ChatGPT prompt for batch extraction:** See `CHATGPT_DEEP_RESEARCH_PROMPT_V4.md` in outputs (if available). It tells ChatGPT to extract lab data and editorial quotes from RunRepeat pages for 12 shoes at a time.

### Tier 3: Brand Specs Only (data_confidence = "placeholder")

Absolute last resort. Only brand-claimed specs, no real-world data. Scoring confidence: ±2. Avoid if possible.

---

## 3. Scoring Process (Step by Step)

### For a RunRepeat review:

1. **Read the full review** — editorial section, not just the lab table
2. **Extract all lab data** into a working note (the key measurements listed in Section 2)
3. **Score the 6 feel dimensions** using the mapping tables in `SHOE_SCORING_FRAMEWORK.md`:
   - Cushion: HA/AC → table → adjust for stack height
   - Bounce: Energy return % → table → adjust for plate presence
   - Stability: Torsional rigidity + heel counter + heel width → composite
   - Rocker: Editorial description + stack context → table
   - Ground feel: Forefoot/heel stack → inverted table
   - Weight feel: Weight in grams → table
4. **Show your working** — for each feel score, state the key input and why you chose that number. Format: `C3 (37.1 AC slightly firm + 38mm stack = 3)`
5. **Assign archetypes** — what is this shoe FOR? See archetype rules in the framework
6. **Fill all spec columns** — weight, drop, plate, fit, etc.
7. **Write the 4 text columns:**
   - `why_it_feels_this_way`: 3-5 sentences explaining the ride using feel language (not lab numbers). Cover the dominant characteristics.
   - `avoid_if`: 2-3 sentences on who should NOT buy this shoe. Be specific and honest.
   - `notable_detail`: 2-3 sentences on what makes this shoe distinctive or interesting.
   - `common_issues`: Pipe-separated `key:value` format. E.g. `durability:heel padding wears quickly | stability:narrow heel platform | sizing:runs slightly small`
8. **Fill `similar_to`** — 2-3 shoes that a runner considering this shoe should also look at
9. **Sanity check against calibration anchors** — does your scoring make sense relative to the nearest anchor shoe?

### For a Tier 2 estimated entry:

1. Search for the shoe: `[brand] [model] specs weight stack review [year]`
2. Find at least 2 trusted editorial sources
3. Extract: weight, stack height, drop, foam type, plate (Y/N + material), brand price
4. Score feel dimensions with ±1 confidence, using editorial descriptions + foam type knowledge
5. Mark `data_confidence: estimated`
6. Note in `notable_detail` if data is limited

### For batch processing (ChatGPT-assisted):

1. Send ChatGPT the extraction prompt with 12 shoe names
2. ChatGPT returns lab data + editorial quotes per shoe
3. YOU (Claude) then score each shoe using that data + the framework
4. Never let ChatGPT assign the 1-5 feel scores — it doesn't know the calibration

---

## 4. Output Format

**TSV file for Google Sheets paste.** One row per shoe, tab-separated, no header row (the header is already in the sheet).

**File naming:** `epic8_batch[N]_[count]shoes.tsv`

**Present each batch with a scoring summary table:**

```
| Shoe | C | B | S | R | G | W | Key call |
|------|---|---|---|---|---|---|----------|
| Name | 3 | 4 | 2 | 3 | 2 | 2 | Brief rationale for the trickiest score |
```

This lets the human verify scores at a glance without reading every TSV row.

---

## 5. Hard-Won Lessons (Don't Repeat These Mistakes)

### Scoring mistakes we caught and fixed:

1. **Don't conflate cushion and bounce.** NB 1080 v13 is cushion 5 but bounce 2. The foam is ultra-soft but returns zero energy. These are independent dimensions.

2. **Stability requires ALL THREE sub-factors.** Torsional rigidity 5 + heel counter 5 + 72mm heel width = stability 2, not 4. The Takumi Sen 11 taught us this. Platform width matters as much as structural rigidity.

3. **Rocker 4-5 is rare.** Most shoes are 1-3. Only ~15% of 185 shoes score 4+. If a review says "moderate rocker" that's a 3, not a 4. Reserve 4-5 for shoes where reviewers use words like "aggressive", "extreme", or "one of the most rockered."

4. **Bounce 5 without a plate is extremely rare.** Only the adidas EVO SL (78.5% return) and the Hyperboost Edge (73.6%) qualify. If there's no plate and energy return is <73%, max bounce is 4.

5. **Trail context shifts bounce and rocker norms.** A trail shoe with 65% energy return is exceptional (score 4). A trail shoe with "moderate rocker" is a 2, not a 3 — trail norms are flatter.

6. **Dual-foam shoes: score based on the feel, not the best foam layer.** If the top foam is soft PEBA but the bottom is firm EVA carrier (like the On Cloudmonster Hyper), the overall ride is firmer than the PEBA alone suggests. Don't score the headline foam — score the experience.

7. **Weight feel is the most objective dimension.** Don't overthink it. Under 210g = 1, 210-250g = 2, 250-270g = 3, 270-300g = 4, over 300g = 5. Almost no exceptions.

8. **The Nimbus 25 does NOT have a plate.** ChatGPT once incorrectly flagged it as having a carbon plate. Always verify plate presence — never trust a single source.

9. **On shoes and CloudTec:** The hollowed-out CloudTec design doesn't change the durometer reading but does change the ride feel. Score based on the editorial description of the ride, not just the lab measurement.

10. **"Aggressive forefoot" heel geometry** is a hard filter in the recommendation engine (-40 for heel strikers). Only use for shoes like the Mizuno Wave Rebellion Pro 3 that would genuinely be uncomfortable for heel strikers. Most shoes are "standard."

### Process mistakes we caught and fixed:

1. **Text columns initially contained RunRepeat lab measurements** (e.g., "10.0 HA durometer"). We had to rewrite 40+ shoes to remove specific numbers. Write feel consequences from the start.

2. **common_issues format:** Use pipe-separated `key:value` pairs, NOT JSON arrays. E.g., `durability:heel padding wears quickly | stability:narrow heel | sizing:runs small`

3. **On Cloudmonster v1 was entered as a duplicate.** Always check for existing entries before adding a shoe.

4. **Release status matters for recommendation quality.** Don't mark discontinued shoes as "available." Use "rare to find" for shoes 2+ generations old that are still findable at discount, and "previous_gen" for the generation immediately before current.

---

## 6. Quality Checkpoints

Before delivering any batch:

- [ ] All 39 columns populated (no blanks where a value is required)
- [ ] shoe_id continues from last used ID
- [ ] Enum values match exactly (check capitalisation)
- [ ] Booleans are TRUE/FALSE
- [ ] Feel scores are integers 1-5 (no decimals, no 0s)
- [ ] Weight is in grams (not ounces)
- [ ] Drop is in mm
- [ ] Text columns contain no specific lab measurements
- [ ] common_issues uses pipe-separated key:value format
- [ ] data_confidence is set correctly (lab/estimated/placeholder)
- [ ] No duplicate shoes
- [ ] Scoring summary table accompanies the TSV

---

## 7. Current Database Stats (as of March 2026)

- **185 shoes total**
- **Last shoe_id used:** shoe_0185
- **Brands covered:** Nike, adidas, ASICS, New Balance, Brooks, Saucony, HOKA, On, Altra, Mizuno, PUMA, Salomon, Skechers, Topo Athletic, Inov-8, Under Armour, The North Face, R.A.D, Li-Ning, Dynafish
- **Data confidence mix:** ~120 lab, ~60 estimated, ~5 placeholder
- **Scoring framework version:** 1.0 (based on 100 shoes, validated against 185)

---

## 8. Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| SHOE_SCORING_FRAMEWORK.md | Project knowledge | Lab-to-score mapping tables, calibration anchors, edge cases, scoring checklist |
| EPIC8_BRIEF.md | Project knowledge | Original epic brief with schema definition |
| shoebase.json | Project knowledge | Current shoe database (may be behind the spreadsheet) |
| ChatGPT prompt V4 | Previous outputs | Batch extraction prompt for previous-gen shoes |

---

## 9. When to Push Back

A good scorer challenges assumptions. Push back when:

- A shoe's marketing claims don't match editorial consensus (e.g., "bouncy" shoe with 50% energy return)
- A shoe is being assigned too many archetypes (most shoes are 1-2, max 3)
- Super trainer designation is being used loosely (it requires genuinely handling easy through interval pace)
- A score doesn't make sense relative to the calibration anchors
- The human asks you to score a shoe you can't find reliable data for (request more sources rather than guessing)

---

## 10. The Golden Rules

1. **Consistency over precision.** It's better to score a shoe 3 when it might be a 4, than to use different logic than the other 185 shoes.
2. **The framework is the authority.** If your instinct disagrees with the mapping tables, check the calibration anchors before overriding.
3. **Show your working.** Always explain why you chose each feel score. This catches mistakes.
4. **Text columns describe the experience, not the measurement.** Feel consequences, not lab numbers.
5. **When in doubt, ask.** If the data is ambiguous, say so rather than guessing silently.
