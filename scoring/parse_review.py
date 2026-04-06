"""Parse a RunRepeat review text file into structured lab data JSON.

Extracts all measurable lab data from a pasted RunRepeat review, plus
editorial context needed for scoring.

Usage:
    python parse_review.py scoring/reviews/runrepeat/nike-pegasus-42.txt

Output: JSON file in scoring/scored/{shoe-name}-parsed.json
"""

import json
import re
import sys
from pathlib import Path

SCORED_DIR = Path(__file__).resolve().parent / "scored"


def parse_review(text: str, source_path: str = "") -> dict:
    """Parse a RunRepeat review text into structured data.

    Extracts lab measurements, shoe metadata, and editorial context.
    Returns a dict ready for the scoring engine.
    """
    data = {
        "shoe_name": "",
        "brand": "",
        "model": "",
        "version": "",
        "source": "runrepeat",
        "data_tier": "lab",
        "lab_data": {},
        "editorial_summary": "",
        "rocker_description": "",
        "raw_text_path": source_path,
    }

    # ── Extract shoe name from title line ──
    # RunRepeat titles are usually like "Nike Pegasus 41 Review" or similar
    title_match = re.search(r'^(.+?)(?:\s+Review|\s+Lab|\s+Test)', text, re.MULTILINE | re.IGNORECASE)
    if title_match:
        data["shoe_name"] = title_match.group(1).strip()

    # ── Brand/model/version parsing ──
    if data["shoe_name"]:
        parts = data["shoe_name"].split()
        if parts:
            data["brand"] = parts[0]
            # Version is usually the last numeric part
            version_match = re.search(r'(\d+(?:\.\d+)?)\s*$', data["shoe_name"])
            if version_match:
                data["version"] = version_match.group(1)
                model_part = data["shoe_name"][len(data["brand"]):].strip()
                model_part = model_part[:model_part.rfind(data["version"])].strip()
                data["model"] = model_part
            else:
                data["model"] = " ".join(parts[1:])

    # ── Extract lab measurements ──
    lab = {}

    # Midsole softness (HA)
    ha_match = re.search(r'(?:midsole\s+)?(?:softness|durometer|hardness)\s*(?:\(HA\))?\s*[:=]?\s*([\d.]+)\s*(?:HA|ha)', text, re.IGNORECASE)
    if not ha_match:
        ha_match = re.search(r'([\d.]+)\s*HA\b', text)
    if ha_match:
        lab["midsole_softness_ha"] = float(ha_match.group(1))

    # Midsole softness (AC / Asker C)
    ac_match = re.search(r'(?:midsole\s+)?(?:softness|durometer)\s*(?:\(AC\))?\s*[:=]?\s*([\d.]+)\s*(?:AC|ac|Asker\s*C)', text, re.IGNORECASE)
    if not ac_match:
        ac_match = re.search(r'([\d.]+)\s*(?:AC|Asker\s*C)\b', text)
    if ac_match:
        lab["midsole_softness_ac"] = float(ac_match.group(1))

    # Energy return
    er_match = re.search(r'(?:energy\s+return|energy return\s+heel)\s*[:=]?\s*([\d.]+)\s*%', text, re.IGNORECASE)
    if not er_match:
        er_match = re.search(r'([\d.]+)\s*%\s*(?:energy\s+return)', text, re.IGNORECASE)
    if er_match:
        lab["energy_return_heel_pct"] = float(er_match.group(1))

    # Shock absorption
    sa_match = re.search(r'shock\s+absorption\s*(?:heel)?\s*[:=]?\s*([\d.]+)', text, re.IGNORECASE)
    if sa_match:
        lab["shock_absorption_heel"] = float(sa_match.group(1))

    # Stack heights
    heel_stack = re.search(r'(?:heel|rear)\s+(?:stack|height)\s*[:=]?\s*([\d.]+)\s*(?:mm)?', text, re.IGNORECASE)
    if heel_stack:
        lab["heel_stack_mm"] = float(heel_stack.group(1))

    forefoot_stack = re.search(r'(?:forefoot|front|fore)\s+(?:stack|height)\s*[:=]?\s*([\d.]+)\s*(?:mm)?', text, re.IGNORECASE)
    if forefoot_stack:
        lab["forefoot_stack_mm"] = float(forefoot_stack.group(1))

    # Drop
    drop_match = re.search(r'(?:heel[- ]toe\s+)?drop\s*(?:\(measured\))?\s*[:=]?\s*([\d.]+)\s*(?:mm)?', text, re.IGNORECASE)
    if drop_match:
        lab["drop_mm_measured"] = float(drop_match.group(1))

    # Weight
    weight_match = re.search(r'weight\s*[:=]?\s*([\d.]+)\s*(?:g|grams)', text, re.IGNORECASE)
    if weight_match:
        lab["weight_g"] = float(weight_match.group(1))

    # Width measurements
    width_match = re.search(r'(?:overall\s+)?width\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if width_match:
        lab["width_mm"] = float(width_match.group(1))

    toebox_w = re.search(r'toe\s*box\s+width\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if toebox_w:
        lab["toebox_width_mm"] = float(toebox_w.group(1))

    toebox_h = re.search(r'toe\s*box\s+height\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if toebox_h:
        lab["toebox_height_mm"] = float(toebox_h.group(1))

    # Flexibility
    flex_match = re.search(r'(?:flexibility|stiffness)\s*[:=]?\s*([\d.]+)\s*(?:N|newtons)', text, re.IGNORECASE)
    if flex_match:
        lab["flexibility_n"] = float(flex_match.group(1))

    # Torsional rigidity (1-5)
    torsion = re.search(r'torsional\s+(?:rigidity|stiffness)\s*[:=]?\s*(\d)\s*(?:/\s*5|out of 5)?', text, re.IGNORECASE)
    if torsion:
        lab["torsional_rigidity_1to5"] = int(torsion.group(1))

    # Heel counter stiffness (1-5)
    heel_counter = re.search(r'heel\s+counter\s+(?:stiffness|rigidity)\s*[:=]?\s*(\d)\s*(?:/\s*5|out of 5)?', text, re.IGNORECASE)
    if heel_counter:
        lab["heel_counter_stiffness_1to5"] = int(heel_counter.group(1))

    # Midsole widths
    ms_fw = re.search(r'midsole\s+width\s+forefoot\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if ms_fw:
        lab["midsole_width_forefoot_mm"] = float(ms_fw.group(1))

    ms_hw = re.search(r'midsole\s+width\s+heel\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if ms_hw:
        lab["midsole_width_heel_mm"] = float(ms_hw.group(1))

    # Outsole durability
    outsole = re.search(r'outsole\s+(?:durability|wear)\s*[:=]?\s*([\d.]+)\s*mm', text, re.IGNORECASE)
    if outsole:
        lab["outsole_durability_mm"] = float(outsole.group(1))

    # Wet grip
    grip = re.search(r'wet\s+(?:grip|traction)\s*[:=]?\s*([\d.]+)', text, re.IGNORECASE)
    if grip:
        lab["wet_grip_traction"] = float(grip.group(1))

    # Plate detection
    plate_patterns = [
        r'carbon\s+(?:fiber|fibre)\s+plate',
        r'carbon\s+plate',
        r'nylon\s+plate',
        r'fiberglass\s+plate',
        r'propulsion\s+plate',
    ]
    lab["has_plate"] = False
    lab["plate_material"] = None
    for pp in plate_patterns:
        if re.search(pp, text, re.IGNORECASE):
            lab["has_plate"] = True
            if "carbon" in pp:
                lab["plate_material"] = "carbon"
            elif "nylon" in pp:
                lab["plate_material"] = "nylon"
            elif "fiberglass" in pp:
                lab["plate_material"] = "fiberglass"
            break

    # Foam type
    foam_patterns = [
        r'(?:foam|midsole)\s+(?:material|type|tech)\s*[:=]?\s*([A-Za-z][\w\s]+)',
        r'(?:uses?|features?|with)\s+(\w+(?:\s+\w+)?)\s+(?:foam|midsole)',
    ]
    for fp in foam_patterns:
        foam_match = re.search(fp, text, re.IGNORECASE)
        if foam_match:
            lab["foam_type"] = foam_match.group(1).strip()
            break

    # Price
    price_gbp = re.search(r'[£]([\d.]+)', text)
    price_usd = re.search(r'\$([\d.]+)', text)
    if price_gbp:
        lab["price_gbp"] = float(price_gbp.group(1))
    elif price_usd:
        lab["price_usd"] = float(price_usd.group(1))

    data["lab_data"] = lab

    # ── Editorial summary (first 3 paragraphs) ──
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 50]
    data["editorial_summary"] = "\n\n".join(paragraphs[:3])

    # ── Rocker description ──
    rocker_patterns = [
        r'(?:rocker|geometry|transition|heel[- ]toe|toe[- ]spring|forefoot[- ]rocker)[^.]*\.',
    ]
    rocker_sentences = []
    for rp in rocker_patterns:
        for match in re.finditer(rp, text, re.IGNORECASE):
            rocker_sentences.append(match.group(0).strip())
    data["rocker_description"] = " ".join(rocker_sentences[:3])

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_review.py <review_file.txt>")
        print("       python parse_review.py scoring/reviews/runrepeat/*.txt")
        sys.exit(1)

    SCORED_DIR.mkdir(exist_ok=True)

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            print(f"  File not found: {filepath}")
            continue

        print(f"  Parsing: {path.name}...", end=" ")
        text = path.read_text(encoding="utf-8", errors="ignore")
        result = parse_review(text, str(path))

        # Save parsed data
        shoe_slug = re.sub(r'[^a-z0-9]+', '-', result.get("shoe_name", path.stem).lower()).strip('-')
        out_path = SCORED_DIR / f"{shoe_slug}-parsed.json"
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"-> {out_path.name}")

        # Summary
        lab = result["lab_data"]
        found = sum(1 for v in lab.values() if v is not None)
        print(f"    {result['shoe_name']} | {found} lab fields extracted")


if __name__ == "__main__":
    main()
