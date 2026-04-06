# Cinda Shoe Scoring Framework

> **Version:** 1.1
> **Updated:** March 2026
> **Based on:** 185 shoes scored across 10 batches (lab + estimated + placeholder)
> **Purpose:** Prevent scoring drift, enable consistent scoring by any LLM or human scorer
> **Companion doc:** `SHOE_SCORING_HANDOFF.md` covers process, column schema, and output format

---

## How to Use This Document

Before scoring any shoe, read Sections 1-3. Use Section 4 as a lookup reference during scoring. Use Section 5 to validate your scores against known anchors.

**Golden Rule:** When in doubt, score conservatively toward the middle (3). Extreme scores (1 or 5) should be reserved for genuinely extreme shoes.

---

## 1. The Six Feel Dimensions

Each shoe gets a 1-5 score on six dimensions. These are **subjective-feeling scales grounded in lab data** — they represent how the shoe *feels* to run in, not raw measurements.

| Dimension | What It Measures | 1 Means | 5 Means |
|-----------|-----------------|---------|---------|
| **cushion_softness** | How soft/plush the midsole feels underfoot | Firm, minimal padding | Cloud-like, marshmallow |
| **bounce** | How much energy the shoe returns per stride | Dead, zero rebound | Explosive, trampoline-like |
| **stability** | How secure/controlled the platform feels laterally | Wobbly, narrow, zero support | Locked-down, wide, guided |
| **rocker** | How aggressively the shoe rolls you forward | Flat, classic, natural toe-off | Extreme forward propulsion |
| **ground_feel** | How connected to the ground you feel | Total isolation, zero feedback | Barefoot-like, every pebble |
| **weight_feel** | How heavy the shoe feels on foot | Featherweight, disappears | Brick, noticeably heavy |

### Key Principle: Dimensions Are Independent

A shoe can be soft (cushion 5) but dead (bounce 2) — see NB 1080 v13.
A shoe can be bouncy (bounce 5) but firm (cushion 3) — see adidas EVO SL.
A shoe can be light (weight 1) but stiff (rocker 3) — see Takumi Sen 11.

Never assume one dimension implies another.

---

## 2. Lab Data → Score Mapping

These ranges are derived from 185 shoes and represent the **primary input** for each dimension. They are guidelines, not rigid thresholds — contextual factors (stack height, plate presence, foam layering) can shift a score ±1.

### 2.1 Cushion Softness

Primary inputs: Midsole softness (HA or AC), stack height

| Score | HA Range | AC Range | Stack Context | Typical Feel |
|-------|----------|----------|---------------|--------------|
| 1 | >25 HA | >45 AC | <28mm heel | Firm, minimal |
| 2 | 22-25 HA | 40-45 AC | 28-32mm heel | Below average |
| 3 | 18-22 HA | 33-40 AC | 32-36mm heel | Average, balanced |
| 4 | 12-18 HA | 27-33 AC | 35-40mm heel | Soft, plush |
| 5 | <12 HA | <27 AC | >37mm heel | Ultra-plush, marshmallow |

**Modifier rules:**
- Tall stack (>38mm) can push a 3 to 4 even with average softness
- Low stack (<28mm) caps cushion at 2 regardless of foam softness
- Dual-foam: score based on the layer the foot sits on (primary foam), but firm secondary layer can pull score down by 1
- CloudTec pods (On shoes): add some perceived compression but don't change durometer — typically doesn't move score

### 2.2 Bounce (Energy Return)

Primary inputs: Energy return %, plate presence, plate material

| Score | Energy Return | Plate | Typical Feel |
|-------|--------------|-------|--------------|
| 1 | <52% | None | Dead, zero rebound |
| 2 | 52-58% | None or nylon | Muted, low energy |
| 3 | 58-66% | None or nylon/fiberglass | Noticeable but moderate |
| 4 | 66-73% | Any (or exceptional no-plate) | Strong, propulsive |
| 5 | >73% | Carbon (or elite no-plate) | Explosive, world-class |

**Modifier rules:**
- Carbon plate adds perceived propulsion — can push 65%+ to a 4 even without 66% threshold
- No plate caps bounce at 4 in most cases (exception: adidas EVO SL at 78.5% gets 5 without plate)
- Dual-foam with inferior base layer: average the feel, don't just use top foam's return
- Trail shoes: energy return context shifts — 65%+ on trail is exceptional (score 4)

### 2.3 Stability

Primary inputs: Torsional rigidity (1-5), heel counter stiffness (1-5), midsole width heel (mm), midsole width forefoot (mm), support_type

| Score | Torsional | Heel Counter | Heel Width | Typical Feel |
|-------|-----------|-------------|------------|--------------|
| 1 | 1-2 | 1-2 | <78mm | Wobbly, zero support |
| 2 | 2-3 | 2-3 | 78-88mm | Minimal, lean-prone |
| 3 | 3-4 | 3 | 88-93mm | Adequate, neutral |
| 4 | 4-5 | 4-5 | 93-97mm | Solid, controlled |
| 5 | 5 | 5 | >97mm | Maximum, guided |

**Modifier rules:**
- All three sub-factors matter — a shoe with torsional 5/5 but 78mm heel platform gets stability 2 (e.g., Takumi Sen 11)
- Stability-labelled shoes (support_type = "stability") should score ≥4
- Ultra-soft foam (cushion 5) inherently reduces perceived stability — can pull score down by 1
- Wide forefoot platform (>117mm) adds to stability perception even without other features

### 2.4 Rocker

Primary inputs: RunRepeat rocker description, heel bevel aggressiveness, toe spring height, stack height

| Score | Geometry | Typical Feel |
|-------|----------|--------------|
| 1 | Flat, classic, no curvature, natural toe-off | Traditional, foot-powered |
| 2 | Mild heel bevel and/or subtle forefoot curve | Slightly smoothed transitions |
| 3 | Moderate rocker, noticeable but not extreme | Rolling motion present |
| 4 | Aggressive forefoot rocker and/or pronounced heel bevel | Strong forward propulsion |
| 5 | Extreme continuous curvature, 4-5cm+ toe spring | Feels like rolling on a ball |

**Modifier rules:**
- Stack height amplifies rocker perception — same geometry feels more rockered at 45mm than 30mm
- Trail shoes: aggressive rocker is less common and less desirable — score relative to trail norms (a moderate trail rocker = 2)
- Heel bevel alone (without forefoot rocker) = score 2, not higher
- Shoes described as "one of the most rockered tested" or with ~5cm toe spring = 4-5

### 2.5 Ground Feel

Primary inputs: Heel stack (mm), forefoot stack (mm)

| Score | Forefoot Stack | Heel Stack | Typical Feel |
|-------|---------------|------------|--------------|
| 1 | >33mm | >40mm | Total isolation |
| 2 | 28-33mm | 35-40mm | Mostly isolated |
| 3 | 25-28mm | 32-35mm | Balanced |
| 4 | 22-25mm | 28-32mm | Connected, good feedback |
| 5 | <22mm | <28mm | Barefoot-like, every pebble |

**Modifier rules:**
- Ground feel is primarily about stack height, not foam softness
- Very soft foam at moderate stack can feel more isolated — pull toward lower ground feel
- Rock plates in trail shoes block some ground sensation — pull ground feel down by 1
- This dimension is **inversely mapped** to stack height in the recommendation engine (ground_feel 1 = max stack, ground_feel 5 = minimal stack)

### 2.6 Weight Feel

Primary inputs: Weight (g)

| Score | Weight Range | Typical Feel |
|-------|-------------|--------------|
| 1 | <210g | Featherweight, disappears |
| 2 | 210-250g | Light, nimble |
| 3 | 250-270g | Average, unremarkable |
| 4 | 270-300g | Noticeable, substantial |
| 5 | >300g | Heavy, brick-like |

**Modifier rules:**
- Weight feel is the most objective dimension — rarely needs adjustment from the table
- Trail shoes: slightly higher weight tolerance (shift ranges up ~15g) because runners expect heft
- Super shoes at 200-210g: if they feel remarkably light for their stack, score 1

---

## 3. Non-Feel Column Guide

### 3.1 Archetype Booleans

A shoe can have multiple archetypes. Use these rules:

| Archetype | Criteria |
|-----------|----------|
| **is_daily_trainer** | Designed for regular daily runs, easy to moderate pace, versatile |
| **is_super_trainer** | Can do daily runs AND tempo/workout — typically has plate or high energy return, versatile across paces |
| **is_recovery_shoe** | Explicitly designed for easy/recovery runs — max cushion, low energy return bias, heavy is OK |
| **is_workout_shoe** | Designed for tempo, intervals, fartlek — responsive, lower weight, higher bounce |
| **is_race_shoe** | Designed for race day — carbon plate, ultra-light, max energy return, limited durability |
| **is_trail_shoe** | Designed for off-road — lugged outsole, protective features |
| **is_walking_shoe** | Suitable for casual walking — typically daily trainers or recovery shoes with good comfort |

**Common combos:**
- Daily trainer + walking shoe (most cushioned dailies)
- Daily trainer + workout shoe (versatile dailies like Pegasus)
- Super trainer = daily + workout (but NOT race)
- Race shoe only (pure race day)
- Trail + race (trail racers like Tecton X3)
- Recovery + walking + daily (plush shoes like Bondi 9)

**Super trainer rule:** A super trainer is a shoe that genuinely works for both daily runs and faster workouts. It typically has a plate or exceptional energy return and weighs under 270g. If it's too heavy or dead for speed work, it's just a daily trainer.

### 3.2 Support Type

| Value | When to Use |
|-------|------------|
| `neutral` | No stability features, designed for neutral runners |
| `stability` | Explicitly marketed as a stability/support shoe (e.g., Kayano, Adrenaline GTS, Guide, Arahi) |

**Note:** The framework previously defined `stable_neutral` and `max_stability` but in practice the database uses only `neutral` and `stability`. Keep it simple.

### 3.3 Heel Geometry

| Value | When to Use |
|-------|------------|
| `standard` | Normal heel shape (vast majority of shoes) |
| `aggressive_forefoot` | Extreme forefoot-biased geometry — very low or negative drop, extreme heel bevel that punishes heel striking (e.g., Mizuno Wave Rebellion Pro 3) |

**Important:** This is a hard filter in the recommendation engine. `aggressive_forefoot` shoes get -40 for heel strikers. Only use for shoes that would genuinely be uncomfortable/problematic for heel strikers due to geometry.

### 3.4 Fit Fields

| Field | Options | Guide |
|-------|---------|-------|
| **fit_volume** | low / standard / high | Based on width measurement: <93mm = low, 93-96mm = standard, >96mm = high |
| **toe_box** | narrow / standard / roomy | Based on toebox width: <71mm = narrow, 71-75mm = standard, >75mm = roomy |
| **width_options** | "standard only" / "standard and wide" | What's actually sold |

### 3.5 Wet Grip

| Value | Traction Score |
|-------|---------------|
| `excellent` | >0.65 |
| `good` | 0.50-0.65 |
| `average` | 0.40-0.50 or no data |
| `poor` | <0.40 |

### 3.6 Price Category

| Value | GBP Range |
|-------|-----------|
| `Budget` | <£100 |
| `Core` | £100-£150 |
| `Premium` | £150-£220 |
| `Super-premium` | >£220 |

### 3.7 Release Status

| Value | When to Use |
|-------|------------|
| `available` | Currently for sale in UK |
| `not yet released` | Announced, not yet available |
| `previous_gen` | Superseded by a newer version but still findable at retail/discount |
| `rare to find` | 2+ generations old, only findable at deep discount or resale |

### 3.8 Heel Drop (Recorded)

Use the **measured** drop from RunRepeat, not the brand-claimed drop. Round to nearest integer. Common discrepancies:
- HOKA: typically 2-4mm higher than claimed
- Most brands: within 1mm of claimed

### 3.9 Data Confidence

| Value | When to Use |
|-------|------------|
| `lab` | Scored primarily from RunRepeat lab review data |
| `estimated` | Scored from editorial reviews + brand specs (no RunRepeat lab data) |
| `placeholder` | Scored from brand specs only — minimal real-world data |

### 3.10 Common Issues Format

Use pipe-separated `key:value` pairs:

```
durability:heel padding wears quickly | stability:narrow heel platform limits support | sizing:runs slightly small
```

NOT JSON arrays. NOT bullet points. Each issue is a short `category:description` pair.

---

## 4. Edge Case Decision Rules

These are the tricky calls we've encountered across 185 shoes. Refer to these when unsure.

### 4.1 When Does Bounce Get 5?

Bounce 5 requires **elite energy return + propulsion mechanism**:
- Energy return >73% with carbon plate → 5
- Energy return >76% without plate → 5 (rare — only EVO SL qualifies at 78.5%)
- Energy return 70-73% with carbon plate → 4 (not 5)
- Energy return >73% but shoe is a *trail* shoe → 4 (trail context caps at 4 unless truly exceptional)

**Current bounce 5 shoes (18):** adidas EVO SL, adidas EVO SL Woven (est.), adidas EVO SL EXO (est.), adidas Adios Pro 3, adidas Adios Pro 4, adidas Hyperboost Edge, adidas Prime X3 Strung, adidas Takumi Sen 11, ASICS Metaspeed Sky Paris, ASICS Metaspeed Edge Tokyo, Brooks Hyperion Elite 5, HOKA Cielo X1 2.0, HOKA Cielo X1 3.0, Li-Ning Red Hare 9 Ultra (est.), Li-Ning Feidian 6 Elite (est.), Nike Alphafly Next% 3, Nike Vaporfly Next% 2, Nike Vaporfly Next% 4, PUMA Deviate NITRO Elite 3, PUMA Deviate NITRO Elite 4 (est.), PUMA Fast-R NITRO Elite 2, Saucony Endorphin Elite 2

### 4.2 When Does Cushion Get 5?

Cushion 5 requires **ultra-soft foam AND generous stack**:
- HA <12 with stack >34mm → 5
- AC <25 with stack >35mm → 5
- Soft foam (HA 12-15) with extremely tall stack (>40mm) → can push to 5
- Soft foam but low stack (<30mm) → caps at 3 regardless

**Current cushion 5 shoes (16):** Brooks Glycerin Max, Brooks Hyperion Max 3, HOKA Bondi 9, Li-Ning Red Hare 9 Ultra (est.), NB 1080 v13, NB 1080 v14, NB 1080 v15, NB FuelCell Rebel v5, NB Fresh Foam X More v6, Nike Invincible 2, Nike Invincible 3, Nike Pegasus Premium, Nike Vomero Plus, Nike Vomero Premium, Saucony Triumph 23

### 4.3 When Does Rocker Get 5?

Rocker 5 is reserved for shoes with **extreme, unmistakable continuous curvature**:
- ~5cm+ toe spring AND pronounced heel bevel AND high stack → 5
- Described by reviewers as "one of the most rockered" → 5 candidate
- Aggressive forefoot only (without extreme heel bevel) → 4 max
- High stack amplifies rocker — same geometry at 45mm feels more rockered than at 30mm

**Current rocker 5 shoes (6):** Skechers Aero Burst, adidas Prime X3 Strung, PUMA Fast-R NITRO Elite 2, Mizuno Wave Rebellion Flash 3, HOKA Rocket X2, HOKA Cielo X1 3.0

### 4.4 Ground Feel for Trail Shoes

Trail shoes have an inherent ground feel disconnect:
- Trail shoes have thick outsoles and often rock plates that block sensation
- A 25mm forefoot trail shoe with a rock plate feels less connected than a 25mm road shoe
- Score trail shoes 1 point lower on ground feel than the stack-height table suggests, if they have a rock plate

### 4.5 When Is a Shoe a Recovery Shoe?

A shoe qualifies as `is_recovery_shoe: true` when:
- Cushion ≥4 AND weight ≥270g AND designed for easy pace
- OR explicitly marketed as recovery (e.g., HOKA Bondi, NB More)
- NOT just because it's soft — it also needs to be *slow* (low bounce, heavy)

A super trainer is NOT a recovery shoe (too responsive/light).

### 4.6 Dual-Foam Shoes

Many modern shoes use two foam layers. Scoring rules:
- **Cushion:** Score based on the layer the foot sits on (top foam), but if the secondary layer is notably firm, pull cushion down by 1
- **Bounce:** Average the perceived feel — don't score based on the top foam alone if the base is dead EVA
- **Example:** On Cloudmonster 3 Hyper has soft PEBA top + firm EVA CloudTec carrier → cushion 3, not 4-5, because the carrier mutes the PEBA

---

## 5. Calibration Anchors

These shoes define the scoring scale. When scoring a new shoe, compare it to the most similar anchor.

### Cushion Softness Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Saucony Kinvara 16 | 27.5 HA, only 28mm stack — firm and minimal |
| 2 | On Cloudrunner 2 | 48.6 AC, 33.6mm — firm daily trainer |
| 3 | Nike Pegasus 41 | Average softness, average stack — the dead centre |
| 4 | ASICS Novablast 5 | Soft FF Blast Max, 37mm stack — clearly plush |
| 5 | NB 1080 v13 | 10.0 HA, ultra-marshmallow — softest ever tested |

### Bounce Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | On Cloudflow 5 | 46.9% energy return — lifeless |
| 2 | Brooks Glycerin 22 | ~55% return, no plate — muted |
| 3 | ASICS Novablast 5 | 66% return but no plate — bouncy for a daily |
| 4 | Saucony Endorphin Speed 4 | 74.5% + nylon plate — strong propulsion |
| 5 | adidas EVO SL | 78.5% without plate — explosive, highest no-plate return |

### Stability Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | adidas Takumi Sen 11 | 72.6mm heel, heel counter 1/5 — narrowest ever |
| 2 | Nike Pegasus Premium | Soft foam, narrow heel, torsional 2/5 |
| 3 | Nike Pegasus 41 | Average everything — balanced neutral |
| 4 | HOKA Bondi 9 | Wide platforms, torsional 4/5, heel counter 5/5 |
| 5 | ASICS Gel Kayano 32 | Full stability tech, widest platforms, max support |

### Rocker Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Brooks Ghost Max 3 | Completely flat, classic, zero rocker geometry |
| 2 | HOKA Bondi 9 | Mild meta-rocker — subtle heel-to-toe smoothing, nothing aggressive |
| 3 | On Cloudmonster 2 | Moderate rocker — rolling but not aggressive |
| 4 | Nike Vomero Premium | Aggressive forefoot rocker, pronounced heel bevel, tall stack amplifies |
| 5 | Mizuno Wave Rebellion Flash 3 | ~5cm toe spring + extreme heel bevel — most aggressive geometry in DB |

### Ground Feel Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | HOKA Bondi 9 | 39mm+ stack — total isolation from ground |
| 2 | ASICS Superblast 2 | 36/30mm stack — mostly isolated but not completely |
| 3 | Saucony Ride 18 | ~33/25mm stack — balanced |
| 4 | Nike Pegasus 41 | ~32/24mm — connected, good road feedback |
| 5 | Saucony Kinvara 16 | 28/23.5mm stack — feel every surface change |

### Weight Feel Anchors
| Score | Anchor | Why |
|-------|--------|-----|
| 1 | Nike Streakfly 2 | 128g — lightest in database by far |
| 2 | adidas EVO SL | 223g — light, nimble super trainer |
| 3 | Saucony Ride 18 | 255g — average, unremarkable |
| 4 | Nike Pegasus 41 | 281g — noticeable, substantial |
| 5 | Nike Vomero Premium | 326g — heaviest in database |

---

## 6. Common Scoring Mistakes to Avoid

1. **Conflating cushion and bounce.** A shoe can be very soft (cushion 5) but dead (bounce 2). Softness ≠ energy return.

2. **Giving trail shoes road-shoe scores.** Trail shoes should be scored in their own context for bounce and rocker, but use the same absolute scale for cushion, stability, ground feel, and weight.

3. **Over-scoring rocker.** Most shoes are a 2 or 3. Only extreme geometries get 4-5. A "noticeable" rocker is a 3, not a 4.

4. **Under-scoring ground feel for low-stack shoes.** A shoe with 23mm forefoot stack absolutely gets ground feel 4-5, even if the foam is soft.

5. **Assuming plate = high bounce.** Nylon and fiberglass plates add stiffness but don't necessarily add bounce. Only carbon plates with high energy return foam reliably push bounce to 4-5.

6. **Scoring stability based only on torsional rigidity.** Heel width matters just as much. A torsionally rigid shoe with an 80mm heel is still unstable.

7. **Forgetting that weight_feel is absolute.** A 280g trail shoe and a 280g road shoe both get weight_feel 4. Don't adjust for category.

8. **Trusting a single data source for plate presence.** Always verify — ChatGPT once incorrectly flagged the Nimbus 25 as having a carbon plate.

9. **Scoring dual-foam shoes based on the headline foam only.** The experience is the composite of both layers. A PEBA top on an EVA base rides firmer than PEBA alone.

---

## 7. Scoring Checklist

For each shoe, work through this in order:

1. **Read the full review** — don't skip to the lab data table
2. **Note the foam type and durometer** → initial cushion score
3. **Check stack height** → does it confirm or override the foam-based cushion score?
4. **Check energy return %** → initial bounce score
5. **Check plate presence and material** → adjust bounce if needed
6. **Check torsional rigidity + heel counter + heel width** → stability score
7. **Read the rocker description** → rocker score
8. **Check forefoot and heel stack** → ground feel score (inverted)
9. **Check weight** → weight feel score
10. **Assign archetypes** — what is this shoe *for*?
11. **Assign fit fields** from measurements
12. **Write why_it_feels_this_way** — 3-5 sentences describing the ride experience (NO specific lab measurements — feel consequences only)
13. **Write avoid_if** — 2-3 sentences on who should NOT buy this shoe
14. **Sanity check** — compare against the closest anchor shoe. Do your scores make sense relative to that anchor?

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial framework based on 100 shoes |
| 1.1 | Mar 2026 | Updated to 185 shoes. Added bounce/cushion/rocker 5 shoe lists. Filled in missing rocker 2/4 and ground feel 2/4 anchors. Updated bounce 4 anchor to Endorphin Speed 4. Added weight 2/4 anchors. Clarified support_type to neutral/stability only. Fixed release_status enums to match actual database. Added data_confidence and common_issues format to Section 3. Added dual-foam edge case rule (4.6). Fixed scoring checklist step 12 to say "no lab measurements in text." Added mistake #8 (single source plate verification) and #9 (dual-foam scoring). |
