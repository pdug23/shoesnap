# ShoeSnap — Shoe Intelligence Workbench

This is the pre-production pipeline for **Cinda**, a running shoe intelligence app. It handles everything before a shoe enters Cinda: image processing, logo processing, scoring from reviews, and database management.

## Repo Structure

```
images/pipeline/     Shoe image processing (bg removal, canvas, WebP)
logos/pipeline/      Brand logo fetching and SVG processing
scoring/             Scoring pipeline (reviews → scores → database)
  reviews/runrepeat/ RunRepeat lab review text files (Tier 1)
  framework/         Scoring framework v1.1 + calibration anchors
  output/batches/    Historic and new batch TSV exports
database/            shoebase.json (the living shoe database)
monitoring/          Future: release tracking, price monitoring
```

## Key Files

- `database/shoebase.json` — 180 shoes, 20 brands, the production database
- `scoring/framework/SCORING_FRAMEWORK.md` — THE authority for scoring. Read before scoring any shoe.
- `scoring/framework/SCORING_HANDOFF.md` — Process, column schema, data tiers
- `scoring/framework/calibration_anchors.json` — Machine-readable anchors

## Running Things

```bash
py main.py                           # CLI menu (all pipelines)
py images/pipeline/shoe_processor.py # Drag-and-drop image processing
py images/pipeline/fetch_shoes.py    # Fetch shoe images from Bing
py logos/pipeline/fetch_logos.py      # Fetch brand logos
py logos/pipeline/process_logos.py    # Process raw logos → SVG
py scoring/parse_review.py <file>    # Parse RunRepeat review → JSON
py scoring/score_shoe.py <file>      # Score parsed review → scored JSON + report
py scoring/validate_batch.py <files> # Validate before export
py scoring/export_tsv.py <files>     # Export to TSV for Sheets
py scoring/update_shoebase.py <files># Merge into shoebase.json
py database/health_check.py          # Database stats and gap analysis
```

## Scoring Rules (Condensed)

Six feel dimensions, each 1-5. Dimensions are INDEPENDENT.

| Dim | 1 | 3 | 5 |
|-----|---|---|---|
| Cushion | Firm, minimal | Average, balanced | Marshmallow |
| Bounce | Dead, zero rebound | Moderate | Explosive |
| Stability | Wobbly, no support | Adequate neutral | Maximum guided |
| Rocker | Flat, classic | Moderate rolling | Extreme propulsion |
| Ground Feel | Total isolation | Balanced | Barefoot-like |
| Weight | Featherweight | Average | Brick |

**Golden rules:**
1. Consistency over precision — check anchors before overriding
2. Never conflate cushion and bounce (they're independent)
3. Rocker 4-5 is rare (~15% of DB). "Moderate" = 3, not 4
4. Text columns describe FEEL, never lab measurements
5. data_confidence: "lab" (RunRepeat), "estimated" (editorial), "placeholder" (brand specs only)

## Data Tiers

1. **RunRepeat** (lab) — Gold standard. Cut shoes in half.
2. **Editorial** (estimated) — Doctors of Running, Believe in the Run, etc. ±1 confidence.
3. **Brand specs** (placeholder) — Last resort. ±2 confidence.

## Column Schema

40 columns. See `scoring/framework/SCORING_HANDOFF.md` for full schema. Key enums:
- Booleans: TRUE/FALSE
- shoe_id: shoe_0186, shoe_0187, etc. (continue from last)
- fit_volume: low / standard / high
- toe_box: narrow / standard / roomy
- width_options: "standard only" / "standard and wide"
- support_type: neutral / stable_neutral / stability
- heel_geometry: standard / aggressive_forefoot
- surface: road / road/trail / trail
- wet_grip: poor / average / good / excellent
- release_status: "rare to find" / "available" / "not yet released"
- retail_price_category: Budget / Core / Premium / Super-premium
- data_confidence: lab / estimated / placeholder
- plate_material: carbon / nylon / fiberglass / (empty if no plate)

**Use ONLY these values. No exceptions.**

## Image Pipeline Spec

- Canvas: 400x250px, transparent background
- Shoe: centred, max 350x200px
- Format: WebP, quality 82, targeting 40-80KB
- Toe direction: right (auto-mirrored)
- Pipeline: defringe → feather → white balance → contrast → mirror → canvas → sharpen → WebP

## Logo Spec

- Canvas: 400x160px viewBox
- Colour: white on transparent
- Format: SVG (preferred) or WebP fallback
- Naming: {brand}-logo.svg
