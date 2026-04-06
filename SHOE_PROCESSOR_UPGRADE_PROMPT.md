# Claude Code Prompt: Shoe-Processor → Cinda Shoe Intelligence Workbench

## What You Are

You are helping build the pre-production pipeline for **Cinda**, a running shoe intelligence app. This repo — currently called `shoe-processor` — handles everything that happens BEFORE a shoe enters the Cinda product: image processing, scoring from reviews, and database management.

You are a senior engineering partner, not a passive assistant. Challenge assumptions, propose better abstractions, and flag risks. The goal is a tool that is genuinely excellent, not just functional.

---

## PART 1: CONTEXT AND HISTORY

### What Cinda Is

Cinda is a running intelligence app that helps runners understand their shoe setup and choose the next shoe to add or replace. It uses a hybrid model: structured UI for data capture, AI for analysis and insight. The product has a recommendation engine that scores shoes against user profiles using a database of running shoes, each scored on six "feel" dimensions.

### What This Repo Does Today

The repo currently handles **shoe image processing**:
- Downloads shoe images from names listed in `shoes.txt`
- User picks the best images
- Processes them (background removal, standardisation) so they're Cinda-ready
- Also handles brand logo fetching and processing

### Current Repo Structure (flat, organic growth)

```
shoe-processor/
├── __pycache__/
├── .claude/                    # Claude Code config (already exists)
├── downloaded_files/           # Raw downloaded images
├── fetched/                    # Fetched resources
├── logos/                      # Processed logos
├── logos_raw/                  # Raw logos
├── output/                     # Processed output
├── background_remover.py
├── brands.txt
├── fetch_logos.py
├── fetch_shoes.py
├── image_pipeline.py
├── logo_pipeline.py
├── main.py
├── process_logos.py
├── README.md
├── requirements.txt
├── run.bat
├── run.sh
├── shoe_processor.py
└── shoes.txt
```

### What We're Adding: A Scoring Pipeline

We want to add shoe scoring capabilities to this repo, transforming it from an image processor into a complete **shoe intelligence workbench**. The scoring pipeline takes shoe reviews (primarily from RunRepeat lab reviews), extracts data, scores shoes against our calibrated framework, and outputs database-ready entries.

### Why This Repo (Not a Separate One)

This is the pre-Cinda pipeline. Image processing and scoring are two stages of the same workflow: score a shoe → approve it → process its images → it's Cinda-ready. They share a common queue (shoe names) and a common database reference (shoebase.json). Keeping them together is cleaner than managing three repos.

---

## PART 2: THE SCORING FRAMEWORK (CRITICAL — READ ALL OF THIS)

### History

We built this scoring framework across Epic 8 (Feb–Mar 2026). The database grew from 72 shoes to 185 shoes across 10+ batches. The framework was created to prevent scoring drift — so that any new scorer (human or LLM) produces scores consistent with the existing 185.

The framework is the single most important asset in this system. It is the authority. If instinct disagrees with the mapping tables, check the calibration anchors before overriding.

### The Six Feel Dimensions

Each shoe gets a 1-5 score on six dimensions. These are **subjective-feeling scales grounded in lab data** — they represent how the shoe FEELS to run in, not raw measurements.

| Dimension | What It Measures | 1 Means | 5 Means |
|-----------|-----------------|---------|---------|
| cushion_softness | How soft/plush the midsole feels | Firm, minimal padding | Cloud-like, marshmallow |
| bounce | How much energy the shoe returns | Dead, zero rebound | Explosive, trampoline-like |
| stability | How secure the platform feels laterally | Wobbly, narrow, zero support | Locked-down, wide, guided |
| rocker | How aggressively it rolls you forward | Flat, classic, natural toe-off | Extreme forward propulsion |
| ground_feel | How connected to the ground you feel | Total isolation, zero feedback | Barefoot-like, every pebble |
| weight_feel | How heavy the shoe feels on foot | Featherweight, disappears | Brick, noticeably heavy |

**KEY PRINCIPLE: Dimensions are independent.** A shoe can be soft (cushion 5) but dead (bounce 2) — see NB 1080 v13. A shoe can be bouncy (bounce 5) but firm (cushion 3) — see adidas EVO SL. Never assume one dimension implies another.

### Lab Data → Score Mapping Tables

#### Cushion Softness
Primary inputs: Midsole softness (HA or AC), stack height

| Score | HA Range | AC Range | Stack Context | Typical Feel |
|-------|----------|----------|---------------|--------------|
| 1 | >25 HA | >45 AC | <28mm heel | Firm, minimal |
| 2 | 22-25 HA | 40-45 AC | 28-32mm heel | Below average |
| 3 | 18-22 HA | 33-40 AC | 32-36mm heel | Average, balanced |
| 4 | 12-18 HA | 27-33 AC | 35-40mm heel | Soft, plush |
| 5 | <12 HA | <27 AC | >37mm heel | Ultra-plush, marshmallow |

Modifiers:
- Tall stack (>38mm) can push 3→4 even with average softness
- Low stack (<28mm) caps cushion at 2 regardless of foam softness
- Dual-foam: score based on foot-contact layer, but firm secondary pulls down by 1
- CloudTec pods (On): perceived compression but doesn't change durometer — typically no score change

#### Bounce (Energy Return)
Primary inputs: Energy return %, plate presence, plate material

| Score | Energy Return | Plate | Typical Feel |
|-------|--------------|-------|--------------|
| 1 | <52% | None | Dead, zero rebound |
| 2 | 52-58% | None or nylon | Muted, low energy |
| 3 | 58-66% | None or nylon/fiberglass | Noticeable but moderate |
| 4 | 66-73% | Any (or exceptional no-plate) | Strong, propulsive |
| 5 | >73% | Carbon (or elite no-plate) | Explosive, world-class |

Modifiers:
- Carbon plate adds perceived propulsion — can push 65%+ to 4 without hitting 66%
- No plate caps bounce at 4 (exception: EVO SL at 78.5% gets 5 without plate)
- Dual-foam with inferior base: average the feel, don't use top foam's return alone
- Trail shoes: context shifts — 65%+ is exceptional (score 4)

#### Stability
Primary inputs: Torsional rigidity (1-5), heel counter stiffness (1-5), midsole width heel (mm)

| Score | Torsional | Heel Counter | Heel Width | Typical Feel |
|-------|-----------|-------------|------------|--------------|
| 1 | 1-2 | 1-2 | <78mm | Wobbly, zero support |
| 2 | 2-3 | 2-3 | 78-88mm | Minimal, lean-prone |
| 3 | 3-4 | 3 | 88-93mm | Adequate, neutral |
| 4 | 4-5 | 4-5 | 93-97mm | Solid, controlled |
| 5 | 5 | 5 | >97mm | Maximum, guided |

Modifiers:
- All three sub-factors matter — torsional 5 + 72mm heel = stability 2 (Takumi Sen 11)
- Stability-labelled shoes should score ≥4
- Ultra-soft foam (cushion 5) reduces perceived stability — pull down by 1
- Wide forefoot (>117mm) adds stability perception

#### Rocker
Primary inputs: Rocker description, heel bevel, toe spring height, stack height

| Score | Geometry | Typical Feel |
|-------|----------|--------------|
| 1 | Flat, classic, no curvature | Traditional, foot-powered |
| 2 | Mild heel bevel and/or subtle forefoot curve | Slightly smoothed |
| 3 | Moderate rocker, noticeable but not extreme | Rolling motion present |
| 4 | Aggressive forefoot and/or pronounced heel bevel | Strong forward propulsion |
| 5 | Extreme continuous curvature, 4-5cm+ toe spring | Rolling on a ball |

Modifiers:
- Stack amplifies rocker — same geometry feels more rockered at 45mm than 30mm
- Trail shoes: moderate trail rocker = 2, not 3
- Heel bevel alone (no forefoot rocker) = 2 max
- Reviewers say "one of the most rockered" or ~5cm toe spring = 4-5

#### Ground Feel
Primary inputs: Heel stack (mm), forefoot stack (mm)

| Score | Forefoot Stack | Heel Stack | Typical Feel |
|-------|---------------|------------|--------------|
| 1 | >33mm | >40mm | Total isolation |
| 2 | 28-33mm | 35-40mm | Mostly isolated |
| 3 | 25-28mm | 32-35mm | Balanced |
| 4 | 22-25mm | 28-32mm | Connected, good feedback |
| 5 | <22mm | <28mm | Barefoot-like, every pebble |

Modifiers:
- Primarily about stack height, not foam softness
- Very soft foam at moderate stack can feel more isolated — pull lower
- Rock plates in trail shoes block sensation — pull down by 1

#### Weight Feel
Primary inputs: Weight (g)

| Score | Weight Range | Typical Feel |
|-------|-------------|--------------|
| 1 | <210g | Featherweight, disappears |
| 2 | 210-250g | Light, nimble |
| 3 | 250-270g | Average, unremarkable |
| 4 | 270-300g | Noticeable, substantial |
| 5 | >300g | Heavy, brick-like |

Modifiers:
- Most objective dimension — rarely needs adjustment
- Trail shoes: shift ranges up ~15g (runners expect heft)
- Super shoes at 200-210g that feel remarkably light = score 1

### Calibration Anchors (v1.1 — These Define the Scale)

#### Cushion Softness
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Saucony Kinvara 16 | 27.5 HA, only 28mm stack — firm and minimal |
| 2 | On Cloudrunner 2 | 48.6 AC, 33.6mm — firm daily trainer |
| 3 | Nike Pegasus 41 | Average softness, average stack — dead centre |
| 4 | ASICS Novablast 5 | Soft FF Blast Max, 37mm stack — clearly plush |
| 5 | NB 1080 v13 | 10.0 HA, ultra-marshmallow — softest ever tested |

#### Bounce
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | On Cloudflow 5 | 46.9% energy return — lifeless |
| 2 | Brooks Glycerin 22 | ~55% return, no plate — muted |
| 3 | ASICS Novablast 5 | 66% return but no plate — bouncy for a daily |
| 4 | Saucony Endorphin Speed 4 | 74.5% + nylon plate — strong propulsion |
| 5 | adidas EVO SL | 78.5% without plate — explosive, highest no-plate return |

#### Stability
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | adidas Takumi Sen 11 | 72.6mm heel, heel counter 1/5 — narrowest ever |
| 2 | Nike Pegasus Premium | Soft foam, narrow heel, torsional 2/5 |
| 3 | Nike Pegasus 41 | Average everything — balanced neutral |
| 4 | HOKA Bondi 9 | Wide platforms, torsional 4/5, heel counter 5/5 |
| 5 | ASICS Gel Kayano 32 | Full stability tech, widest platforms, max support |

#### Rocker
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Brooks Ghost Max 3 | Completely flat, classic, zero rocker |
| 2 | HOKA Bondi 9 | Mild meta-rocker — subtle, nothing aggressive |
| 3 | On Cloudmonster 2 | Moderate rocker — rolling but not aggressive |
| 4 | Nike Vomero Premium | Aggressive forefoot, pronounced heel bevel, tall stack amplifies |
| 5 | Mizuno Wave Rebellion Flash 3 | ~5cm toe spring + extreme heel bevel — most aggressive in DB |

#### Ground Feel
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | HOKA Bondi 9 | 39mm+ stack — total isolation |
| 2 | ASICS Superblast 2 | 36/30mm stack — mostly isolated |
| 3 | Saucony Ride 18 | ~33/25mm stack — balanced |
| 4 | Nike Pegasus 41 | ~32/24mm — connected, good feedback |
| 5 | Saucony Kinvara 16 | 28/23.5mm stack — feel every surface change |

#### Weight Feel
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Nike Streakfly 2 | 128g — lightest in database |
| 2 | adidas EVO SL | 223g — light, nimble |
| 3 | Saucony Ride 18 | 255g — average, unremarkable |
| 4 | Nike Pegasus 41 | 281g — noticeable, substantial |
| 5 | Nike Vomero Premium | 326g — heaviest in database |

### Edge Case Decision Rules

**Bounce 5:** Requires elite energy return + propulsion mechanism. >73% with carbon plate → 5. >76% without plate → 5 (rare — only EVO SL). 70-73% with carbon → 4, not 5.

**Cushion 5:** Requires ultra-soft foam AND generous stack. HA <12 with stack >34mm → 5. Soft foam but low stack (<30mm) → caps at 3.

**Rocker 5:** Reserved for extreme continuous curvature. ~5cm+ toe spring AND pronounced heel bevel AND high stack → 5. Most shoes are 2-3. Only ~15% of 185 shoes score 4+.

**Dual-foam shoes:** Score based on composite feel. PEBA top + firm EVA base rides firmer than PEBA alone. Cushion: score foot-contact layer but firm secondary pulls down by 1. Bounce: average the perceived feel.

**Trail shoe adjustments:** Bounce context shifts (65%+ = exceptional, score 4). Rocker: moderate trail rocker = 2. Ground feel: rock plates pull down by 1.

**Recovery shoe criteria:** All daily trainers and super trainers are also recovery shoes. If you can run daily miles in it, you can do recovery runs in it. Do NOT gate recovery on weight or bounce — the database consistently applies this rule across all 180 shoes.

### Common Scoring Mistakes (Hard-Won Lessons from 185 Shoes)

1. **Don't conflate cushion and bounce.** NB 1080 v13 is cushion 5 but bounce 2. Independent dimensions.
2. **Stability requires ALL THREE sub-factors.** Torsional 5 + heel counter 5 + 72mm heel width = stability 2. Platform width matters as much as structural rigidity.
3. **Rocker 4-5 is rare.** "Moderate rocker" = 3, not 4. Reserve 4-5 for "aggressive" or "extreme" language.
4. **Bounce 5 without plate is extremely rare.** Only EVO SL qualifies. No plate + <73% = max 4.
5. **Trail context shifts bounce and rocker norms.**
6. **Dual-foam: score the experience, not the headline foam.**
7. **Weight feel is absolute.** 280g trail shoe and 280g road shoe both get 4.
8. **Verify plate presence from multiple sources.** ChatGPT once wrongly flagged Nimbus 25 as having carbon plate.
9. **On shoes and CloudTec:** Hollowed design doesn't change durometer but changes ride feel. Score from editorial description.
10. **"Aggressive forefoot" heel geometry** is a hard filter (-40 for heel strikers). Only for genuinely problematic geometry.

### Column Schema (39 columns + data_confidence = 40 total)

Column order (exact):
```
shoe_id | brand | model | version | full_name | alias_code | is_daily_trainer | is_super_trainer | is_recovery_shoe | is_workout_shoe | is_race_shoe | is_trail_shoe | is_walking_shoe | cushion_softness_1to5 | bounce_1to5 | stability_1to5 | rocker_1to5 | ground_feel_1to5 | weight_feel_1to5 | weight_g | heel_drop_mm | has_plate | plate_tech_name | plate_material | fit_volume | toe_box | width_options | support_type | heel_geometry | surface | wet_grip | release_status | release_year | release_quarter | retail_price_category | why_it_feels_this_way | avoid_if | similar_to | notable_detail | common_issues | data_confidence
```

#### Enum Values (exact strings only):

| Column | Allowed Values |
|--------|---------------|
| fit_volume | low / standard / high |
| toe_box | narrow / standard / roomy |
| width_options | "standard only" / "standard and wide" |
| support_type | neutral / stability |
| heel_geometry | standard / aggressive_forefoot |
| surface | road / trail |
| wet_grip | poor / average / good / excellent |
| release_status | "rare to find" / "available" / "not yet released" / "previous_gen" |
| retail_price_category | Budget / Core / Premium / Super-premium |
| data_confidence | lab / estimated / placeholder |
| plate_material | carbon / nylon / fiberglass / (empty if no plate) |

Boolean fields: TRUE/FALSE (not true/false, not 1/0)
shoe_id format: shoe_0186, shoe_0187, etc. (continue from last used ID in shoebase.json)

#### Text Column Rules:
- `why_it_feels_this_way`: 3-5 sentences explaining the ride using FEEL language. NO specific lab measurements. Say "among the softest midsoles ever tested" not "10.0 HA durometer."
- `avoid_if`: 2-3 sentences on who should NOT buy this shoe. Be specific and honest.
- `notable_detail`: 2-3 sentences on what makes this shoe distinctive.
- `common_issues`: Pipe-separated key:value format. E.g. `durability:heel padding wears quickly | stability:narrow heel | sizing:runs small`
- `similar_to`: 2-3 shoes a runner should also consider.

#### Archetype Rules:
- Most shoes are 1-2 archetypes, max 3
- Super trainer is a high bar — must genuinely handle easy through interval pace, typically has plate or exceptional energy return, weighs under 270g
- Super trainer = daily + workout (NOT race)
- Recovery + walking + daily is a common combo for plush shoes

### Data Source Tiers

**Tier 1: RunRepeat Lab Reviews (data_confidence = "lab")**
Gold standard. They cut shoes in half and measure everything.

Extract from RunRepeat:
- Midsole softness (HA and/or AC)
- Energy return heel %
- Shock absorption heel
- Heel stack (mm) and forefoot stack (mm)
- Drop (mm) — use MEASURED, not brand-claimed
- Weight (g)
- Width/Fit (mm), Toebox width (mm), Toebox height (mm)
- Flexibility/Stiffness (N)
- Torsional rigidity (1-5), Heel counter stiffness (1-5)
- Midsole width forefoot (mm) and heel (mm)
- Outsole durability (mm wear)
- Wet grip traction score
- Price

**Tier 2: Editorial Sources (data_confidence = "estimated")**
Priority order:
1. Doctors of Running
2. Believe in the Run
3. Road Trail Run
4. Running Warehouse reviews
5. Brand specs
6. Supwell (Chinese brands)

Scoring confidence: ±1 on feel scores. Flag as estimated.

**Tier 3: Brand Specs Only (data_confidence = "placeholder")**
Absolute last resort. ±2 confidence. Avoid.

### The Scoring Process (14-Step Checklist)

For each shoe:
1. Read the full review — don't skip to the lab table
2. Note foam type and durometer → initial cushion score
3. Check stack height → confirm or override cushion
4. Check energy return % → initial bounce score
5. Check plate presence and material → adjust bounce
6. Check torsional rigidity + heel counter + heel width → stability
7. Read rocker description → rocker score
8. Check forefoot and heel stack → ground feel (inverted)
9. Check weight → weight feel
10. Assign archetypes — what is this shoe FOR?
11. Assign fit fields from measurements
12. Write text columns — feel consequences only, NO lab numbers
13. Write avoid_if — be specific and honest
14. Sanity check against calibration anchors

### The Golden Rules
1. **Consistency over precision.** Score 3 when it might be 4, rather than use different logic than the other 185 shoes.
2. **The framework is the authority.** Check anchors before overriding.
3. **Show your working.** Format: `C3 (37.1 AC slightly firm + 38mm stack = 3)`
4. **Text describes experience, not measurement.**
5. **When in doubt, ask.** Don't guess silently.

### Current Database Stats
- 185 shoes total
- Last shoe_id: shoe_0185
- 20 brands
- ~120 lab, ~60 estimated, ~5 placeholder
- Framework version: 1.1

---

## PART 3: THE RESTRUCTURE

### Target Structure

Reorganise the flat repo into a clean multi-pipeline structure:

```
shoe-processor/
├── .claude/                         # Existing Claude Code config
├── CLAUDE.md                        # Master context file (THE source of truth for Claude Code sessions)
├── README.md
├── requirements.txt
├── run.sh
├── run.bat
├── main.py                          # CLI entry point — menu-driven
│
├── images/                          # Image processing pipeline
│   ├── pipeline/
│   │   ├── fetch_shoes.py
│   │   ├── background_remover.py
│   │   ├── shoe_processor.py
│   │   └── image_pipeline.py
│   ├── downloaded/                  # Raw downloads (was downloaded_files)
│   ├── processed/                   # Cinda-ready output (was output)
│   └── shoes.txt                    # Image queue — auto-populated by scoring
│
├── logos/                           # Logo pipeline (mostly unchanged)
│   ├── pipeline/
│   │   ├── fetch_logos.py
│   │   └── process_logos.py
│   ├── raw/                         # Was logos_raw
│   └── processed/                   # Was logos
│
├── scoring/                         # NEW — Scoring pipeline
│   ├── reviews/                     # All source material stored permanently
│   │   ├── runrepeat/               # RunRepeat lab review text files
│   │   ├── doctors-of-running/      # DoR editorial reviews
│   │   ├── believe-in-the-run/      # BiTR reviews
│   │   └── other/                   # Road Trail Run, Supwell, misc
│   ├── framework/                   # Scoring brain (reference docs)
│   │   ├── SCORING_FRAMEWORK.md     # v1.1 — the authority document
│   │   ├── SCORING_HANDOFF.md       # Process + column schema
│   │   └── calibration_anchors.json # Machine-readable anchors for validation
│   ├── output/
│   │   ├── batches/                 # TSV files ready for Sheets paste
│   │   └── reports/                 # Scoring reasoning per batch
│   ├── scored/                      # Individual scored shoe JSON files (intermediate)
│   ├── score_shoe.py                # Core scoring engine
│   ├── parse_review.py              # Extract structured data from review text
│   ├── validate_batch.py            # Check enums, dupes, ranges, anchor comparison
│   ├── export_tsv.py                # Generate Sheets-ready TSV
│   └── update_shoebase.py           # Merge new shoes into shoebase.json
│
├── database/                        # Living database
│   ├── shoebase.json                # Current production database
│   └── changelog.md                 # What was added, when, by which batch
│
├── brands.txt                       # Brand list
└── fetched/                         # General fetched resources
```

### Restructure Rules

1. **Move files, don't copy.** Git should track the moves.
2. **Update all imports** after moving. Test that everything still works.
3. **Preserve existing functionality.** Image processing and logo processing must work exactly as before after restructure.
4. **Create empty directories** for scoring pipeline folders with `.gitkeep` files where needed.
5. **Update main.py** to be a proper CLI entry point with a menu:
   - `1. Score shoes from reviews`
   - `2. Process shoe images`
   - `3. Process brand logos`
   - `4. Validate database`
   - `5. Export batch to TSV`
6. **Create CLAUDE.md** at root — this is the master context file for all future Claude Code sessions. It should contain a condensed version of the scoring framework, repo structure, and workflow instructions. This is the most important file in the repo.

---

## PART 4: THE SCORING PIPELINE (NEW CODE)

### What to Build

#### 1. `scoring/parse_review.py`
Parses a RunRepeat review text file and extracts structured data.

Input: A `.txt` file containing a pasted RunRepeat review
Output: A JSON object with all extractable lab data:

```json
{
  "shoe_name": "Nike Pegasus 41",
  "brand": "Nike",
  "model": "Pegasus",
  "version": "41",
  "source": "runrepeat",
  "data_tier": "lab",
  "lab_data": {
    "midsole_softness_ha": 19.5,
    "midsole_softness_ac": 37.1,
    "energy_return_heel_pct": 62.3,
    "shock_absorption_heel": null,
    "heel_stack_mm": 33.5,
    "forefoot_stack_mm": 24.0,
    "drop_mm_measured": 9.5,
    "weight_g": 281,
    "width_mm": 94.2,
    "toebox_width_mm": 73.1,
    "toebox_height_mm": null,
    "flexibility_n": null,
    "torsional_rigidity_1to5": 3,
    "heel_counter_stiffness_1to5": 3,
    "midsole_width_forefoot_mm": 115.2,
    "midsole_width_heel_mm": 91.3,
    "outsole_durability_mm": null,
    "wet_grip_traction": 0.52,
    "has_plate": false,
    "plate_material": null,
    "foam_type": "React X",
    "price_gbp": 125
  },
  "editorial_summary": "First 2-3 paragraphs of editorial text for context",
  "rocker_description": "Extracted rocker/geometry description from review",
  "raw_text_path": "scoring/reviews/runrepeat/nike-pegasus-41.txt"
}
```

This should be robust to variations in RunRepeat review format. Not every field will be present — handle nulls gracefully.

#### 2. `scoring/score_shoe.py`
The core scoring engine. This is the most important file.

Input: Either a parsed review JSON (from parse_review.py) or a raw review text file
Output: A complete shoe entry matching the 40-column schema

This script should:
- Load the existing shoebase.json for duplicate checking and next shoe_id
- Load calibration anchors from `framework/calibration_anchors.json`
- Apply the scoring framework mapping tables
- Generate initial scores with reasoning
- Compare against calibration anchors and flag anomalies
- Output both a scoring report (human-readable) and a scored shoe JSON

**Critical:** This script provides the INITIAL scores and reasoning. The human reviews and may adjust. It should be transparent about uncertainty — if a score could be ±1, say so. Show working for every dimension.

The scoring report format:
```
## Nike Pegasus 41 — Scoring Report

### Feel Scores
| Dim | Score | Reasoning |
|-----|-------|-----------|
| C   | 3     | 37.1 AC average softness + 33.5mm stack = solidly average |
| B   | 3     | 62.3% return, no plate = moderate |
| S   | 3     | Torsional 3, heel counter 3, 91.3mm heel = balanced neutral |
| R   | 2     | Mild rocker, nothing aggressive |
| G   | 4     | 24mm forefoot = connected |
| W   | 4     | 281g = noticeable |

### Anchor Comparison
Closest to: Nike Pegasus 41 (it IS the cushion 3 anchor)
All scores align with calibration expectations.

### Flags
- None

### Archetypes: daily_trainer, walking_shoe
### Data Confidence: lab
```

#### 3. `scoring/validate_batch.py`
Validates a batch of scored shoes before export.

Checks:
- All 40 columns populated
- shoe_id continues from last used
- Enum values match exactly (case-sensitive)
- Booleans are TRUE/FALSE
- Feel scores are integers 1-5
- Weight in grams, drop in mm
- Text columns contain no specific lab measurements (flag numbers like "10.0 HA" or "78.5%")
- common_issues uses pipe-separated key:value format
- data_confidence set correctly
- No duplicate shoes (check brand + model + version against shoebase.json)
- Cross-reference feel scores against anchors — flag anything that seems like an outlier

Output: Pass/fail with specific issues listed.

#### 4. `scoring/export_tsv.py`
Generates tab-separated output ready for Google Sheets paste.

Input: One or more scored shoe JSON files
Output: A `.tsv` file in `scoring/output/batches/` with the exact column order defined in the schema. No header row (header already exists in the sheet).

File naming: `batch_NNN_Xshoes.tsv` where NNN auto-increments based on existing batches.

Also generates a scoring summary table:
```
| Shoe | C | B | S | R | G | W | Key call |
|------|---|---|---|---|---|---|----------|
| Nike Pegasus 41 | 3 | 3 | 3 | 2 | 4 | 4 | Dead centre on most dimensions |
```

#### 5. `scoring/update_shoebase.py`
Merges approved shoes into `database/shoebase.json`.

- Validates JSON structure
- Checks for duplicates
- Assigns shoe_ids
- Sorts by brand alphabetically
- Updates changelog.md
- Also appends shoe full_names to `images/shoes.txt` (the image queue)

#### 6. `scoring/framework/calibration_anchors.json`
Machine-readable version of the calibration anchors.

```json
{
  "version": "1.1",
  "anchors": {
    "cushion_softness": {
      "1": { "shoe": "Saucony Kinvara 16", "why": "27.5 HA, 28mm stack", "ha": 27.5, "stack_heel_mm": 28 },
      "2": { "shoe": "On Cloudrunner 2", "why": "48.6 AC, 33.6mm", "ac": 48.6, "stack_heel_mm": 33.6 },
      "3": { "shoe": "Nike Pegasus 41", "why": "Average everything", "ac": 37.1, "stack_heel_mm": 33.5 },
      "4": { "shoe": "ASICS Novablast 5", "why": "Soft FF Blast Max, 37mm", "stack_heel_mm": 37 },
      "5": { "shoe": "NB 1080 v13", "why": "10.0 HA, softest ever", "ha": 10.0, "stack_heel_mm": 38 }
    },
    "bounce": {
      "1": { "shoe": "On Cloudflow 5", "why": "46.9% return", "energy_return_pct": 46.9 },
      "2": { "shoe": "Brooks Glycerin 22", "why": "~55% return, no plate", "energy_return_pct": 55 },
      "3": { "shoe": "ASICS Novablast 5", "why": "66% but no plate", "energy_return_pct": 66 },
      "4": { "shoe": "Saucony Endorphin Speed 4", "why": "74.5% + nylon plate", "energy_return_pct": 74.5 },
      "5": { "shoe": "adidas EVO SL", "why": "78.5% without plate", "energy_return_pct": 78.5 }
    },
    "stability": {
      "1": { "shoe": "adidas Takumi Sen 11", "why": "72.6mm heel", "heel_width_mm": 72.6 },
      "2": { "shoe": "Nike Pegasus Premium", "why": "Soft foam, narrow heel" },
      "3": { "shoe": "Nike Pegasus 41", "why": "Average everything", "heel_width_mm": 91.3 },
      "4": { "shoe": "HOKA Bondi 9", "why": "Wide platforms", "heel_width_mm": 96 },
      "5": { "shoe": "ASICS Gel Kayano 32", "why": "Full stability tech" }
    },
    "rocker": {
      "1": { "shoe": "Brooks Ghost Max 3", "why": "Completely flat" },
      "2": { "shoe": "HOKA Bondi 9", "why": "Mild meta-rocker" },
      "3": { "shoe": "On Cloudmonster 2", "why": "Moderate, rolling" },
      "4": { "shoe": "Nike Vomero Premium", "why": "Aggressive forefoot, tall stack" },
      "5": { "shoe": "Mizuno Wave Rebellion Flash 3", "why": "~5cm toe spring, extreme" }
    },
    "ground_feel": {
      "1": { "shoe": "HOKA Bondi 9", "why": "39mm+ stack", "stack_heel_mm": 39 },
      "2": { "shoe": "ASICS Superblast 2", "why": "36/30mm", "stack_forefoot_mm": 30 },
      "3": { "shoe": "Saucony Ride 18", "why": "33/25mm", "stack_forefoot_mm": 25 },
      "4": { "shoe": "Nike Pegasus 41", "why": "32/24mm", "stack_forefoot_mm": 24 },
      "5": { "shoe": "Saucony Kinvara 16", "why": "28/23.5mm", "stack_forefoot_mm": 23.5 }
    },
    "weight_feel": {
      "1": { "shoe": "Nike Streakfly 2", "why": "128g", "weight_g": 128 },
      "2": { "shoe": "adidas EVO SL", "why": "223g", "weight_g": 223 },
      "3": { "shoe": "Saucony Ride 18", "why": "255g", "weight_g": 255 },
      "4": { "shoe": "Nike Pegasus 41", "why": "281g", "weight_g": 281 },
      "5": { "shoe": "Nike Vomero Premium", "why": "326g", "weight_g": 326 }
    }
  }
}
```

### What the Scoring Scripts Should NOT Do

- **Do not scrape websites.** Reviews are manually downloaded and saved as .txt files.
- **Do not make network requests.** Everything works from local files.
- **Do not assign final scores without showing reasoning.** The human always reviews.
- **Do not put lab measurements in text columns.** Feel consequences only.
- **Do not auto-merge into shoebase.json without explicit human approval.**

---

## PART 5: FUTURE PIPELINE STAGES (BUILD THE HOOKS, NOT THE FEATURES)

Think ahead. Create placeholder directories and stub functions for these future capabilities, but don't build them yet. The architecture should accommodate them without refactoring.

### 5.1 Release Monitoring
Future: Track when new shoes are announced/released. For now, just create `monitoring/` directory with a README explaining the vision.

### 5.2 Review Upgrade Tracking
Future: When a shoe is scored as "estimated" (Tier 2), automatically flag it when RunRepeat publishes a lab review so we can upgrade to "lab" confidence. For now, `update_shoebase.py` should have a `--check-upgrades` stub that lists all estimated shoes.

### 5.3 Database Health Reports
Future: Analyse shoebase.json for gaps — underrepresented archetypes, brands with few shoes, stale release_status, missing similar_to references. For now, create `database/health_check.py` with basic stats: shoe count, brand distribution, archetype distribution, data_confidence breakdown, release_status breakdown.

### 5.4 Competitor Price Tracking
Future: Track shoe prices across retailers. For now, just the directory placeholder.

### 5.5 Seasonal/Release Calendar
Future: Track release cycles so Cinda can recommend shoes that are about to launch or go on sale. Placeholder only.

---

## PART 6: TECHNICAL NOTES

- Python 3.10+
- No external API calls in the scoring pipeline — everything works from local files
- JSON for intermediate data, TSV for final export (Google Sheets compatible)
- Use `pathlib` for path handling
- No new heavy deps for scoring — it's pure Python + JSON
- Keep existing image processing deps intact
- Write a CLAUDE.md at the root that gives any future Claude Code session the full context it needs to work in this repo
