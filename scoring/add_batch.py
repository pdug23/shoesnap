"""One-time script to add 6 new shoes to shoebase.json."""
import json
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "database" / "shoebase.json"
shoes = json.loads(DB.read_text(encoding="utf-8"))
last_id = max(int(s["shoe_id"].split("_")[1]) for s in shoes)

new_shoes = [
    {
        "brand": "adidas", "model": "Adistar", "version": "4",
        "full_name": "adidas Adistar 4",
        "is_daily_trainer": True, "is_super_trainer": False, "is_recovery_shoe": True,
        "is_workout_shoe": False, "is_race_shoe": False, "is_trail_shoe": False, "is_walking_shoe": True,
        "cushion_softness_1to5": 3, "bounce_1to5": 1, "stability_1to5": 4,
        "rocker_1to5": 2, "ground_feel_1to5": 2, "weight_feel_1to5": 4,
        "weight_g": 272, "heel_drop_mm": 5, "has_plate": False,
        "plate_tech_name": None, "plate_material": None,
        "heel_stack_mm": 40.0, "forefoot_stack_mm": 35.0,
        "fit_volume": "standard", "toe_box": "standard", "width_options": "standard and wide",
        "support_type": "neutral", "heel_geometry": "standard", "surface": "road",
        "wet_grip": "good", "release_status": "available", "release_year": 2026,
        "release_quarter": "Q1", "retail_price_category": "Core",
        "why_it_feels_this_way": "A comfort-first daily trainer with generous stack height that absorbs impact well but returns almost nothing. The REPETITOR 2.0 foam feels soft and easygoing underfoot without any bounce or pop, making it ideal for easy-paced miles where energy return is irrelevant. Very stiff heel counter and solid torsional rigidity create a stable platform, especially for heel strikers. The mild rocker feels natural rather than forced.",
        "avoid_if": "Avoid if you want any sense of energy return or speed \u2014 this shoe feels dead flat and unresponsive at faster paces. Poor breathability makes it uncomfortable in hot weather. Not suitable for runners who dislike high-drop geometry.",
        "similar_to": "PUMA Magnify NITRO 3, Brooks Ghost 17, Nike Revolution 8",
        "notable_detail": "One of the most stable neutral shoes in the database thanks to its exceptionally stiff heel counter. The REPETITOR 2.0 foam prioritises comfort over performance. Excellent reflective elements for visibility.",
        "common_issues": ["breathability:poor airflow throughout upper", "responsiveness:essentially zero energy return", "drop:brand claims 5mm but feels noticeably high-drop"],
        "data_confidence": "lab"
    },
    {
        "brand": "adidas", "model": "Terrex Agravic TT", "version": None,
        "full_name": "adidas Terrex Agravic TT",
        "is_daily_trainer": False, "is_super_trainer": False, "is_recovery_shoe": False,
        "is_workout_shoe": True, "is_race_shoe": False, "is_trail_shoe": True, "is_walking_shoe": False,
        "cushion_softness_1to5": 3, "bounce_1to5": 3, "stability_1to5": 3,
        "rocker_1to5": 5, "ground_feel_1to5": 3, "weight_feel_1to5": 5,
        "weight_g": 306, "heel_drop_mm": 8, "has_plate": True,
        "plate_tech_name": "TPE/Fibreglass composite", "plate_material": "fiberglass",
        "heel_stack_mm": 39.0, "forefoot_stack_mm": 31.0,
        "fit_volume": "standard", "toe_box": "narrow", "width_options": "standard only",
        "support_type": "neutral", "heel_geometry": "standard", "surface": "trail",
        "wet_grip": "good", "release_status": "available", "release_year": 2026,
        "release_quarter": "Q1", "retail_price_category": "Premium",
        "why_it_feels_this_way": "A polarising trail shoe built around one of the most extreme rocker designs in the database. The aggressive heel bevel and curved forefoot create a powerful forward-rolling sensation that either feels thrilling or uncontrollable depending on your preference. Lightstrike Pro in the top layer adds softness and energy, while the Lightstrike carrier beneath provides structure. The Continental rubber outsole delivers reliable grip and exceptional durability. Heavy for its class.",
        "avoid_if": "Avoid if you prefer a traditional, predictable trail shoe \u2014 the extreme rocker geometry is genuinely love-it-or-hate-it. Not suitable for muddy or snowy conditions. The narrow toebox and heavy weight make it a poor choice for ultra distances.",
        "similar_to": "HOKA Tecton X 3, HOKA Speedgoat 6, Salomon Speedcross 6",
        "notable_detail": "Features one of the most aggressive rocker profiles ever tested on a trail shoe. The partial-length fiberglass plate splits at both ends for terrain adaptability rather than rigid propulsion. Continental rubber outsole is virtually indestructible.",
        "common_issues": ["weight:heavy for a premium trail shoe", "rocker:extreme geometry is polarising", "toebox:narrow fit with thin upper that lacks durability"],
        "data_confidence": "lab"
    },
    {
        "brand": "Mizuno", "model": "Wave Inspire", "version": "22",
        "full_name": "Mizuno Wave Inspire 22",
        "is_daily_trainer": True, "is_super_trainer": False, "is_recovery_shoe": True,
        "is_workout_shoe": False, "is_race_shoe": False, "is_trail_shoe": False, "is_walking_shoe": True,
        "cushion_softness_1to5": 3, "bounce_1to5": 2, "stability_1to5": 4,
        "rocker_1to5": 2, "ground_feel_1to5": 2, "weight_feel_1to5": 4,
        "weight_g": 294, "heel_drop_mm": 10, "has_plate": True,
        "plate_tech_name": "Wave Plate", "plate_material": "nylon",
        "heel_stack_mm": 38.5, "forefoot_stack_mm": 28.5,
        "fit_volume": "standard", "toe_box": "standard", "width_options": "standard and wide",
        "support_type": "stability", "heel_geometry": "standard", "surface": "road",
        "wet_grip": "good", "release_status": "available", "release_year": 2026,
        "release_quarter": "Q2", "retail_price_category": "Core",
        "why_it_feels_this_way": "A dependable stability trainer that prioritises controlled comfort over excitement. The Enerzy NXT midsole feels soft enough for daily miles but returns very little energy, creating a smooth but flat ride. The Wave Plate in the heel provides structural stability without making the shoe feel rigid. Updated lower drop and added forefoot foam make it more versatile than previous Inspires. Excellent outsole durability for high-mileage runners.",
        "avoid_if": "Avoid if you want any sense of bounce or responsiveness \u2014 the ride is comfortable but lifeless at faster paces. Not for runners who prefer lightweight or minimal shoes. Only addresses mild pronation, so severe overpronators should look elsewhere.",
        "similar_to": "Mizuno Wave Inspire 21, Brooks Adrenaline GTS 24, ASICS Gel Kayano 31",
        "notable_detail": "The lower drop compared to previous Inspires opens the shoe up to midfoot strikers for the first time in the series. Outstanding outsole durability. The Wave Plate is a stability device, not a propulsion plate.",
        "common_issues": ["bounce:flat ride with minimal energy return", "weight:heavier than most modern stability shoes", "pronation:only addresses mild pronation"],
        "data_confidence": "lab"
    },
    {
        "brand": "On", "model": "Cloudmonster", "version": "3",
        "full_name": "On Cloudmonster 3",
        "is_daily_trainer": True, "is_super_trainer": False, "is_recovery_shoe": True,
        "is_workout_shoe": False, "is_race_shoe": False, "is_trail_shoe": False, "is_walking_shoe": True,
        "cushion_softness_1to5": 2, "bounce_1to5": 3, "stability_1to5": 3,
        "rocker_1to5": 4, "ground_feel_1to5": 1, "weight_feel_1to5": 5,
        "weight_g": 301, "heel_drop_mm": 6, "has_plate": True,
        "plate_tech_name": "TPU Speedboard", "plate_material": "nylon",
        "heel_stack_mm": 40.0, "forefoot_stack_mm": 34.0,
        "fit_volume": "standard", "toe_box": "narrow", "width_options": "standard only",
        "support_type": "neutral", "heel_geometry": "standard", "surface": "road",
        "wet_grip": "average", "release_status": "available", "release_year": 2026,
        "release_quarter": "Q2", "retail_price_category": "Premium",
        "why_it_feels_this_way": "A max-stack shoe that feels firm despite its massive platform. The three-layer CloudTec system creates a structured, almost rigid feel underfoot \u2014 nothing sinks or compresses the way traditional soft foam does. Energy return is average, with the TPU Speedboard adding some forward roll but no real pop. The aggressive forefoot rocker is the defining characteristic, creating a strong rolling sensation that drives transitions. Completely isolates you from the ground. Heavy.",
        "avoid_if": "Avoid if you expect soft, plush cushioning from a max-stack shoe \u2014 the CloudTec design feels firm and hollow rather than cushioned. Not for speed work or anyone who values a lightweight shoe. Poor breathability and a narrow toebox limit comfort in warm conditions.",
        "similar_to": "On Cloudmonster 2, On Cloudmonster 3 Hyper, HOKA Bondi 9",
        "notable_detail": "Forefoot rises more than 5cm \u2014 one of the most aggressive forefoot rockers in the database despite the shoe being positioned as a daily trainer. The CloudTec hollow-pod construction means the foam firmness does not tell the full cushioning story. Doubles convincingly as a lifestyle sneaker.",
        "common_issues": ["cushion:feels firm despite max stack", "weight:over 300g is heavy for any road shoe", "breathability:poor airflow", "price:expensive for the performance delivered"],
        "data_confidence": "lab"
    },
    {
        "brand": "Saucony", "model": "Endorphin Pro", "version": "5",
        "full_name": "Saucony Endorphin Pro 5",
        "is_daily_trainer": False, "is_super_trainer": False, "is_recovery_shoe": False,
        "is_workout_shoe": True, "is_race_shoe": True, "is_trail_shoe": False, "is_walking_shoe": False,
        "cushion_softness_1to5": 3, "bounce_1to5": 4, "stability_1to5": 3,
        "rocker_1to5": 4, "ground_feel_1to5": 2, "weight_feel_1to5": 2,
        "weight_g": 215, "heel_drop_mm": 8, "has_plate": True,
        "plate_tech_name": "Speedroll carbon plate", "plate_material": "carbon",
        "heel_stack_mm": 39.5, "forefoot_stack_mm": 31.5,
        "fit_volume": "standard", "toe_box": "narrow", "width_options": "standard only",
        "support_type": "neutral", "heel_geometry": "standard", "surface": "road",
        "wet_grip": "good", "release_status": "available", "release_year": 2026,
        "release_quarter": "Q2", "retail_price_category": "Super-premium",
        "why_it_feels_this_way": "A stable, accessible carbon racer that prioritises control over raw speed. The full-length carbon plate with Saucony's signature Speedroll geometry creates a strong forward-rolling sensation without feeling twitchy or unstable. Moderate cushioning feels balanced rather than extreme \u2014 protective enough for marathon distance but not plush. Light and fast with strong energy return, particularly suited to heel strikers thanks to the pronounced heel flare.",
        "avoid_if": "Avoid if you want the lightest possible race shoe \u2014 at 215g it is heavier than elite competitors. The aggressive Speedroll rocker is polarising; runners who prefer a natural toe-off will find it intrusive. Narrow toebox may cause discomfort over marathon distance.",
        "similar_to": "Saucony Endorphin Pro 4, Saucony Endorphin Elite 2, Nike Vaporfly Next% 4",
        "notable_detail": "The most beginner-friendly carbon super shoe available \u2014 delivers race-day performance with a stable, forgiving platform. Also works as a premium tempo trainer for interval sessions. Excellent outsole durability for a race shoe.",
        "common_issues": ["weight:heavier than most carbon racers", "stiffness:stiffer than some runners prefer", "rocker:Speedroll geometry is love-it-or-hate-it"],
        "data_confidence": "lab"
    },
]

# Add new shoes with IDs
for shoe in new_shoes:
    last_id += 1
    shoe["shoe_id"] = f"shoe_{last_id:04d}"
    shoe["alias_code"] = None
    shoes.append(shoe)
    print(f"  ADD: {shoe['shoe_id']} - {shoe['full_name']}")

# Update CM3 Hyper
for s in shoes:
    if s["shoe_id"] == "shoe_0172":
        s["cushion_softness_1to5"] = 3
        s["bounce_1to5"] = 3
        s["stability_1to5"] = 4
        s["rocker_1to5"] = 4
        s["ground_feel_1to5"] = 1
        s["weight_feel_1to5"] = 3
        s["weight_g"] = 264
        s["heel_drop_mm"] = 6
        s["heel_stack_mm"] = 37.0
        s["forefoot_stack_mm"] = 31.0
        s["data_confidence"] = "lab"
        s["wet_grip"] = "average"
        s["why_it_feels_this_way"] = "A major step forward for On \u2014 the Helion HF foam finally delivers genuine energy and bounce that was missing from previous Cloudmonsters. The ride is firm by super trainer standards but dynamic and engaging, with an aggressive heel bevel and rocker that drive strong forward propulsion. Wide platforms and exceptional torsional rigidity create surprising stability for such a tall stack. Completely isolates you from the ground."
        s["avoid_if"] = "Avoid if you prefer soft, plush cushioning \u2014 the ride is firm and structured despite the massive stack. Limited breathability. The aggressive heel geometry makes it less forgiving for sloppy form."
        s["common_issues"] = ["cushion:firm ride despite max stack", "breathability:limited airflow", "price:expensive even by super trainer standards"]
        print(f"  UPD: shoe_0172 - On Cloudmonster 3 Hyper -> lab")
        break

# Sort and save
shoes.sort(key=lambda s: (s["brand"].lower(), s["model"].lower(), str(s.get("version", ""))))
DB.write_text(json.dumps(shoes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"\nTotal: {len(shoes)} shoes. Saved.")
