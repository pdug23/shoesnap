# ShoeSnap Workflow Guide

## Score a New Shoe

```bash
# 1. Save the RunRepeat review as a text file
#    Copy the full review page text into:
scoring/reviews/runrepeat/shoe-name.txt

# 2. Parse the review (extracts lab data into JSON)
py scoring/parse_review.py scoring/reviews/runrepeat/shoe-name.txt

# 3. Score it (applies framework, generates report)
py scoring/score_shoe.py scoring/scored/shoe-name-parsed.json

# 4. Review the report and edit the scored JSON
#    - Check feel scores against calibration anchors
#    - Fill in text columns (why_it_feels_this_way, avoid_if, etc.)
#    - Set archetypes (is_daily_trainer, is_race_shoe, etc.)
#    - The scored JSON is at: scoring/scored/shoe-name-scored.json

# 5. Validate before export
py scoring/validate_batch.py scoring/scored/shoe-name-scored.json

# 6. Export to TSV (for Google Sheets paste)
py scoring/export_tsv.py scoring/scored/shoe-name-scored.json

# 7. Merge into the database (when approved)
py scoring/update_shoebase.py scoring/scored/shoe-name-scored.json
```

## Upgrade an Estimated Shoe to Lab

Same as above, but instead of merging as a new shoe, you manually
update the existing entry in `database/shoebase.json`:
1. Parse and score the RunRepeat review (steps 1-3)
2. Compare the new lab scores against the existing estimated scores
3. Update the entry in shoebase.json with the lab-backed scores
4. Change `data_confidence` from `"estimated"` to `"lab"`

To see which shoes need upgrading:
```bash
py scoring/update_shoebase.py --check-upgrades
```

## Process Shoe Images

```bash
# Fetch images (GUI — pick best side profile per shoe)
py images/pipeline/fetch_shoes.py

# Process images (drag-and-drop, or Process All)
py images/pipeline/shoe_processor.py
```

## Process Brand Logos

```bash
# Fetch logos (GUI — pick best logo per brand)
py logos/pipeline/fetch_logos.py

# Process raw logos into SVG
py logos/pipeline/process_logos.py
```

## Database Health Check

```bash
py database/health_check.py
```

## Quick Reference

| Task | Command |
|------|---------|
| Menu | `py main.py` |
| Parse review | `py scoring/parse_review.py <file.txt>` |
| Score shoe | `py scoring/score_shoe.py <parsed.json>` |
| Validate | `py scoring/validate_batch.py <scored.json>` |
| Export TSV | `py scoring/export_tsv.py <scored.json>` |
| Merge to DB | `py scoring/update_shoebase.py <scored.json>` |
| Check upgrades | `py scoring/update_shoebase.py --check-upgrades` |
| Process images | `py images/pipeline/shoe_processor.py` |
| Fetch images | `py images/pipeline/fetch_shoes.py` |
| Fetch logos | `py logos/pipeline/fetch_logos.py` |
| Process logos | `py logos/pipeline/process_logos.py` |
| DB health | `py database/health_check.py` |
