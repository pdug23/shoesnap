"""Core scoring engine — applies the Cinda scoring framework to parsed review data.

Takes a parsed review JSON and produces:
1. A scoring report (human-readable reasoning)
2. A scored shoe JSON matching the 40-column schema

The human always reviews and may adjust. This script shows its working
for every dimension and flags uncertainty.

Usage:
    python score_shoe.py scoring/scored/nike-pegasus-42-parsed.json
"""

import json
import sys
from pathlib import Path

SCORING_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCORING_DIR / "framework"
DATABASE_DIR = SCORING_DIR.parent / "database"
REPORTS_DIR = SCORING_DIR / "output" / "reports"
SCORED_DIR = SCORING_DIR / "scored"


def load_anchors() -> dict:
    """Load calibration anchors."""
    anchors_path = FRAMEWORK_DIR / "calibration_anchors.json"
    if anchors_path.exists():
        return json.loads(anchors_path.read_text(encoding="utf-8"))
    return {}


def load_shoebase() -> list:
    """Load the current shoebase for duplicate checking and ID generation."""
    sb_path = DATABASE_DIR / "shoebase.json"
    if sb_path.exists():
        return json.loads(sb_path.read_text(encoding="utf-8"))
    return []


def next_shoe_id(shoebase: list) -> str:
    """Get the next available shoe_id."""
    if not shoebase:
        return "shoe_0001"
    last_id = max(int(s["shoe_id"].split("_")[1]) for s in shoebase)
    return f"shoe_{last_id + 1:04d}"


def check_duplicate(shoebase: list, brand: str, model: str, version: str) -> bool:
    """Check if this shoe already exists in the database."""
    for s in shoebase:
        if (s["brand"].lower() == brand.lower() and
            s["model"].lower() == model.lower() and
            str(s.get("version", "")).lower() == str(version).lower()):
            return True
    return False


# ── Scoring functions ──

def score_cushion(lab: dict) -> tuple[int, str]:
    """Score cushion softness from lab data. Returns (score, reasoning)."""
    ha = lab.get("midsole_softness_ha")
    ac = lab.get("midsole_softness_ac")
    stack = lab.get("heel_stack_mm")

    if ha is not None:
        if ha > 25:
            base = 1
        elif ha > 22:
            base = 2
        elif ha > 18:
            base = 3
        elif ha > 12:
            base = 4
        else:
            base = 5
        measure_str = f"{ha} HA"
    elif ac is not None:
        if ac > 45:
            base = 1
        elif ac > 40:
            base = 2
        elif ac > 33:
            base = 3
        elif ac > 27:
            base = 4
        else:
            base = 5
        measure_str = f"{ac} AC"
    else:
        return 3, "No softness data — defaulting to 3 (NEEDS REVIEW)"

    reason = f"{measure_str}"

    # Stack modifiers
    if stack:
        reason += f" + {stack}mm stack"
        if stack > 38 and base == 3:
            base = 4
            reason += " (tall stack pushes 3->4)"
        elif stack < 28 and base > 2:
            base = 2
            reason += " (low stack caps at 2)"

    return base, reason


def score_bounce(lab: dict) -> tuple[int, str]:
    """Score bounce/energy return."""
    er = lab.get("energy_return_heel_pct")
    has_plate = lab.get("has_plate", False)
    plate_mat = lab.get("plate_material")

    if er is None:
        return 3, "No energy return data — defaulting to 3 (NEEDS REVIEW)"

    if er < 52:
        base = 1
    elif er < 58:
        base = 2
    elif er < 66:
        base = 3
    elif er < 73:
        base = 4
    else:
        base = 5

    reason = f"{er}% return"

    if has_plate:
        reason += f" + {plate_mat or 'unknown'} plate"
        if er >= 65 and base == 3:
            base = 4
            reason += " (plate pushes 3->4)"
    else:
        reason += ", no plate"
        if base == 5 and er < 76:
            base = 4
            reason += " (no plate caps at 4)"

    return base, reason


def score_stability(lab: dict) -> tuple[int, str]:
    """Score lateral stability."""
    torsion = lab.get("torsional_rigidity_1to5")
    heel_counter = lab.get("heel_counter_stiffness_1to5")
    heel_w = lab.get("midsole_width_heel_mm")

    parts = []
    scores = []

    if torsion is not None:
        parts.append(f"torsional {torsion}/5")
        if torsion <= 2:
            scores.append(1)
        elif torsion <= 3:
            scores.append(2.5)
        elif torsion <= 4:
            scores.append(3.5)
        else:
            scores.append(5)

    if heel_counter is not None:
        parts.append(f"heel counter {heel_counter}/5")
        if heel_counter <= 2:
            scores.append(1)
        elif heel_counter <= 3:
            scores.append(2.5)
        elif heel_counter <= 4:
            scores.append(3.5)
        else:
            scores.append(5)

    if heel_w is not None:
        parts.append(f"{heel_w}mm heel")
        if heel_w < 78:
            scores.append(1)
        elif heel_w < 88:
            scores.append(2)
        elif heel_w < 93:
            scores.append(3)
        elif heel_w < 97:
            scores.append(4)
        else:
            scores.append(5)

    if not scores:
        return 3, "No stability data — defaulting to 3 (NEEDS REVIEW)"

    avg = sum(scores) / len(scores)
    base = max(1, min(5, round(avg)))
    reason = ", ".join(parts)

    return base, reason


def score_rocker(lab: dict) -> tuple[int, str]:
    """Score rocker aggressiveness. Mostly from editorial — lab data is limited."""
    rocker_desc = lab.get("_rocker_description", "")

    if not rocker_desc:
        return 2, "No rocker description — defaulting to 2 (NEEDS REVIEW)"

    desc_lower = rocker_desc.lower()

    if any(w in desc_lower for w in ["extreme", "aggressive rocker", "5cm", "most rockered"]):
        return 5, f"Editorial: extreme rocker"
    elif any(w in desc_lower for w in ["aggressive forefoot", "pronounced", "strong rocker"]):
        return 4, f"Editorial: aggressive rocker"
    elif any(w in desc_lower for w in ["moderate rocker", "noticeable", "rolling"]):
        return 3, f"Editorial: moderate rocker"
    elif any(w in desc_lower for w in ["mild", "subtle", "slight", "meta-rocker"]):
        return 2, f"Editorial: mild rocker"
    elif any(w in desc_lower for w in ["flat", "classic", "no rocker", "traditional"]):
        return 1, f"Editorial: flat/no rocker"
    else:
        return 2, f"Rocker description unclear — defaulting to 2 (NEEDS REVIEW)"


def score_ground_feel(lab: dict) -> tuple[int, str]:
    """Score ground feel (inverse of stack height)."""
    forefoot = lab.get("forefoot_stack_mm")
    heel = lab.get("heel_stack_mm")

    # Use forefoot as primary (closer to feel), heel as secondary
    stack = forefoot or heel
    label = "forefoot" if forefoot else "heel"

    if stack is None:
        return 3, "No stack data — defaulting to 3 (NEEDS REVIEW)"

    if forefoot:
        if forefoot > 33:
            base = 1
        elif forefoot > 28:
            base = 2
        elif forefoot > 25:
            base = 3
        elif forefoot > 22:
            base = 4
        else:
            base = 5
    else:
        # Using heel stack
        if heel > 40:
            base = 1
        elif heel > 35:
            base = 2
        elif heel > 32:
            base = 3
        elif heel > 28:
            base = 4
        else:
            base = 5

    reason = f"{stack}mm {label} stack"
    if forefoot and heel:
        reason = f"{heel}/{forefoot}mm stack"

    return base, reason


def score_weight_feel(lab: dict) -> tuple[int, str]:
    """Score perceived weight."""
    weight = lab.get("weight_g")

    if weight is None:
        return 3, "No weight data — defaulting to 3 (NEEDS REVIEW)"

    if weight < 210:
        base = 1
    elif weight < 250:
        base = 2
    elif weight < 270:
        base = 3
    elif weight < 300:
        base = 4
    else:
        base = 5

    return base, f"{weight}g"


# ── Main scoring orchestrator ──

def score_from_parsed(parsed: dict) -> tuple[dict, str]:
    """Score a shoe from parsed review data.

    Returns:
        (scored_shoe_dict, report_text)
    """
    shoebase = load_shoebase()
    anchors = load_anchors()

    lab = parsed.get("lab_data", {})
    # Inject rocker description into lab for the rocker scorer
    lab["_rocker_description"] = parsed.get("rocker_description", "")

    # Check for duplicates
    brand = parsed.get("brand", "")
    model = parsed.get("model", "")
    version = parsed.get("version", "")
    shoe_name = parsed.get("shoe_name", f"{brand} {model} {version}".strip())

    is_dupe = check_duplicate(shoebase, brand, model, version)

    # Score each dimension
    c_score, c_reason = score_cushion(lab)
    b_score, b_reason = score_bounce(lab)
    s_score, s_reason = score_stability(lab)
    r_score, r_reason = score_rocker(lab)
    g_score, g_reason = score_ground_feel(lab)
    w_score, w_reason = score_weight_feel(lab)

    # ── Build scoring report ──
    report_lines = [
        f"## {shoe_name} — Scoring Report",
        "",
        f"Source: {parsed.get('source', 'unknown')} | Data tier: {parsed.get('data_tier', 'unknown')}",
        "",
    ]

    if is_dupe:
        report_lines.append(f"**WARNING: This shoe already exists in the database ({brand} {model} {version})**")
        report_lines.append("")

    report_lines.extend([
        "### Feel Scores",
        "| Dim | Score | Reasoning |",
        "|-----|-------|-----------|",
        f"| C   | {c_score}     | {c_reason} |",
        f"| B   | {b_score}     | {b_reason} |",
        f"| S   | {s_score}     | {s_reason} |",
        f"| R   | {r_score}     | {r_reason} |",
        f"| G   | {g_score}     | {g_reason} |",
        f"| W   | {w_score}     | {w_reason} |",
        "",
    ])

    # Anchor comparison
    report_lines.append("### Anchor Comparison")
    anchor_data = anchors.get("anchors", {})
    dimensions = [
        ("cushion_softness", c_score),
        ("bounce", b_score),
        ("stability", s_score),
        ("rocker", r_score),
        ("ground_feel", g_score),
        ("weight_feel", w_score),
    ]
    for dim_name, dim_score in dimensions:
        dim_anchors = anchor_data.get(dim_name, {})
        anchor = dim_anchors.get(str(dim_score), {})
        if anchor:
            report_lines.append(f"- {dim_name} {dim_score}: anchor is {anchor['shoe']} ({anchor['why']})")

    report_lines.append("")

    # Flags
    flags = []
    needs_review_dims = []
    for label, reason in [("C", c_reason), ("B", b_reason), ("S", s_reason),
                           ("R", r_reason), ("G", g_reason), ("W", w_reason)]:
        if "NEEDS REVIEW" in reason:
            needs_review_dims.append(label)

    if needs_review_dims:
        flags.append(f"Missing data for: {', '.join(needs_review_dims)} — scores need manual review")
    if is_dupe:
        flags.append("DUPLICATE — shoe already in database")

    report_lines.append("### Flags")
    if flags:
        for f in flags:
            report_lines.append(f"- {f}")
    else:
        report_lines.append("- None")

    report_lines.append("")

    # ── Build scored shoe skeleton ──
    shoe_id = next_shoe_id(shoebase)
    scored = {
        "shoe_id": shoe_id,
        "brand": brand,
        "model": model,
        "version": version,
        "full_name": shoe_name,
        "alias_code": None,
        "is_daily_trainer": False,
        "is_super_trainer": False,
        "is_recovery_shoe": False,
        "is_workout_shoe": False,
        "is_race_shoe": False,
        "is_trail_shoe": False,
        "is_walking_shoe": False,
        "cushion_softness_1to5": c_score,
        "bounce_1to5": b_score,
        "stability_1to5": s_score,
        "rocker_1to5": r_score,
        "ground_feel_1to5": g_score,
        "weight_feel_1to5": w_score,
        "weight_g": lab.get("weight_g"),
        "heel_drop_mm": lab.get("drop_mm_measured"),
        "has_plate": lab.get("has_plate", False),
        "plate_tech_name": None,
        "plate_material": lab.get("plate_material"),
        "fit_volume": "standard",
        "toe_box": "standard",
        "width_options": "standard only",
        "support_type": "neutral",
        "heel_geometry": "standard",
        "surface": "road",
        "wet_grip": "average",
        "release_status": "available",
        "release_year": None,
        "release_quarter": None,
        "retail_price_category": "Core",
        "why_it_feels_this_way": "NEEDS HUMAN INPUT — describe the ride feel, not lab numbers",
        "avoid_if": "NEEDS HUMAN INPUT — who should NOT buy this shoe",
        "similar_to": "NEEDS HUMAN INPUT — 2-3 comparable shoes",
        "notable_detail": "NEEDS HUMAN INPUT — what makes this shoe distinctive",
        "common_issues": [],
        "data_confidence": parsed.get("data_tier", "estimated"),
    }

    # Auto-detect some fields from lab data
    toebox_w = lab.get("toebox_width_mm")
    if toebox_w:
        if toebox_w < 68:
            scored["toe_box"] = "narrow"
        elif toebox_w > 75:
            scored["toe_box"] = "roomy"

    grip = lab.get("wet_grip_traction")
    if grip is not None:
        if grip < 0.3:
            scored["wet_grip"] = "poor"
        elif grip < 0.5:
            scored["wet_grip"] = "average"
        elif grip < 0.7:
            scored["wet_grip"] = "good"
        else:
            scored["wet_grip"] = "excellent"

    report_text = "\n".join(report_lines)
    return scored, report_text


def main():
    if len(sys.argv) < 2:
        print("Usage: python score_shoe.py <parsed_review.json>")
        sys.exit(1)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SCORED_DIR.mkdir(exist_ok=True)

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            print(f"  File not found: {filepath}")
            continue

        parsed = json.loads(path.read_text(encoding="utf-8"))
        scored, report = score_from_parsed(parsed)

        shoe_name = scored.get("full_name", "unknown")
        slug = path.stem.replace("-parsed", "")

        # Save scored shoe
        scored_path = SCORED_DIR / f"{slug}-scored.json"
        scored_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")

        # Save report
        report_path = REPORTS_DIR / f"{slug}-report.md"
        report_path.write_text(report, encoding="utf-8")

        print(f"\n{report}")
        print(f"\nScored: {scored_path}")
        print(f"Report: {report_path}")
        print(f"\n** Review the scored JSON and report, then adjust as needed **")


if __name__ == "__main__":
    main()
