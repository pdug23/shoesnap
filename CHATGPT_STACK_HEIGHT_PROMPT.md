# ChatGPT Deep Research Prompt — Stack Height Backfill

Paste this into ChatGPT with Deep Research enabled.

---

I need the **heel stack height (mm)** and **forefoot stack height (mm)** for the following running shoes. These should be **lab-measured values** where possible (from RunRepeat, Doctors of Running, or Believe in the Run), or **brand-claimed specs** as a fallback.

For each shoe, provide the data in this exact format (tab-separated, one shoe per line):

```
shoe_name	heel_stack_mm	forefoot_stack_mm	source
```

Where source is one of: "runrepeat", "doctors_of_running", "believe_in_the_run", "brand_specs"

If you cannot find data for a shoe, write "null" for both values and "not_found" for source.

**Important:**
- Prefer lab-measured over brand-claimed. Brand specs often differ from reality by 1-3mm.
- RunRepeat is the gold standard — they physically cut shoes and measure.
- Heel stack is the thicker measurement, forefoot stack is thinner. The difference is the drop.
- Use men's US size 9 / EU 42.5 measurements where multiple sizes are available.

Here are the 118 shoes:

```
HOKA Bondi 9
HOKA Clifton 10
Nike Vomero Plus
Nike Vomero Premium
New Balance Fresh Foam X More v6
ASICS Novablast 5
Brooks Glycerin Max
New Balance Fresh Foam X 1080 v14
Nike Vomero 18
Nike Pegasus Premium
ASICS Gel Nimbus 27
ASICS Superblast 2
Brooks Ghost Max 3
Skechers Aero Burst
On Cloudmonster 2
On Cloudmonster
New Balance FuelCell Rebel v5
Nike Invincible 3
PUMA Velocity NITRO 4
PUMA MagMax NITRO
adidas Adizero SL 2
Mizuno Neo Zen
Mizuno Neo Vista 2
PUMA Magnify NITRO 3
Salomon Aero Glide 2
Topo Athletic Atmos
Altra Experience Flow 2
PUMA Deviate NITRO Elite 3
adidas Adizero Boston 13
HOKA Mach 6
Saucony Endorphin Speed 5
Saucony Endorphin Elite 2
HOKA Mach X 3
Nike Alphafly Next% 3
Nike Zoom Fly 6
adidas Adizero Adios Pro 4
Saucony Endorphin Pro 4
New Balance FuelCell SuperComp Elite v5
Nike Streakfly 2
ASICS Metaspeed Edge Tokyo
adidas Adizero Prime X3 Strung
PUMA Fast-R NITRO Elite 2
HOKA Challenger 8
New Balance Fresh Foam X Hierro v9
Altra Lone Peak 9
Altra Olympus 6
ASICS Metafuji Trail
The North Face Vectiv Enduris 3
Saucony Triumph 23
Saucony Guide 18
HOKA Arahi 8
Salomon Speedcross 6
ASICS Gel Cumulus 27
Salomon Aero Glide 3
ASICS Gel Nimbus 28
Mizuno Wave Rebellion Pro 3
PUMA Fast-R NITRO Elite 3
ASICS Gel Contend 9
Nike Revolution 8
New Balance Fresh Foam 680 v8
Nike Pegasus Trail 5
Saucony Peregrine 15
ASICS Metaspeed Sky Tokyo
HOKA Clifton 9
HOKA Mach 5
HOKA Bondi 8
Nike Pegasus 40
Nike Alphafly Next% 2
Nike Zoom Fly 5
ASICS Novablast 4
ASICS Gel Kayano 31
Brooks Glycerin 21
Saucony Endorphin Speed 4
New Balance FuelCell Rebel v4
Brooks Ghost 16
Nike Vaporfly Next% 3
ASICS Gel Kayano 30
Brooks Adrenaline GTS 23
Saucony Triumph 22
HOKA Arahi 7
adidas Ultraboost Light
ASICS Gel Cumulus 26
Saucony Ride 17
Brooks Hyperion Max 2
PUMA Velocity NITRO 3
ASICS Gel Nimbus 26
ASICS GT-2000 13
ASICS Superblast
Saucony Endorphin Speed 3
Saucony Guide 17
HOKA Mach X 2
Brooks Ghost 15
HOKA Speedgoat 5
HOKA Clifton 8
Saucony Triumph 21
Nike Vomero 17
R.A.D UFO
Nike Vaporfly NEXT% 2
adidas Adizero Adios Pro 3
adidas Adizero Boston 12
Saucony Endorphin Pro 3
ASICS Metaspeed Sky Paris
Brooks Ghost 14
Nike Invincible 2
adidas Ultraboost 22
ASICS Gel Nimbus 25
Nike Alphafly NEXT%
HOKA Bondi 7
Salomon Speedcross 5
New Balance Ellipse v1
Li-Ning Red Hare 9 Ultra
Li-Ning Feidian 6 Elite
Topo Athletic Atmos 2
Salomon Aero Glide 4 GRVL
PUMA Deviate NITRO 4
PUMA Deviate NITRO Elite 4
Dynafish Xiaonian
Mizuno Hyperwarp Pro
```
