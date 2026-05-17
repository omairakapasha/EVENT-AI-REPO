# Color Scale Generation

## Anchor Placement by Luminance

Relative luminance formula (sRGB):
```
L = 0.2126 * R + 0.7152 * G + 0.0722 * B
(where R, G, B are linearized: c/255 if c <= 0.04045 else ((c/255+0.055)/1.055)^2.4)
```

| Luminance range | Anchor stop | Example |
|-----------------|-------------|---------|
| < 0.10 (very dark) | 700–800 | #1A3D64 navy → 600 |
| 0.10–0.25 (dark) | 600–700 | deep forest green |
| 0.25–0.45 (mid-dark) | 500–600 | medium blue |
| 0.45–0.60 (mid) | 400–500 | #96A78D sage → 400 |
| 0.60–0.80 (light) | 200–300 | sky blue |
| > 0.80 (very light) | 50–100 | #EFECE3 cream → 100 |

## Scale Derivation Rules

Given anchor hex `A` at stop `N`:

**Lighter stops** (50 → N): progressively mix A with white
- 50:  A at 5%  + white 95%
- 100: A at 15% + white 85%
- 200: A at 30% + white 70%
- 300: A at 50% + white 50%
- 400: A at 70% + white 30%  (or anchor if N=400)

**Darker stops** (N → 950): progressively mix A with black
- 700: A at 85% + black 15%
- 800: A at 70% + black 30%
- 900: A at 50% + black 50%
- 950: A at 35% + black 65%

## Pre-computed Scales for Event-AI Palette

### Primary — Navy #1A3D64 (anchor at 600)

```
50:  #edf3fa
100: #d0e2f2
200: #a3c5e5
300: #6fa3d4
400: #4280be
500: #2260a0
600: #1a3d64  ← anchor
700: #153252
800: #0f2540
900: #091829
950: #040c15
```

### Accent — Sage #96A78D (anchor at 400)

```
50:  #f4f6f2
100: #e6ebe2
200: #cdd7c6
300: #b3c3aa
400: #96a78d  ← anchor
500: #7a8f71
600: #617558
700: #4d5d45
800: #394534
900: #252e22
950: #131811
```

### Canvas — Cream #EFECE3 (anchor at 100)

```
50:  #faf9f6
100: #efece3  ← anchor
200: #dedad0
300: #cac5b8
400: #b0a99a
500: #948d7e
600: #787063
700: #5e574d
800: #443f38
900: #2b2823
950: #161411
```

### Surface — Warm neutral (derived from canvas hue)

```
50:  #faf9f6
100: #f2f0ea
200: #e3e0d8
300: #ccc8be
400: #aaa59a
500: #888278
600: #6a6560
700: #504d48
800: #363330
900: #1e1c1a
950: #0f0e0d
```

## Mixing Algorithm (manual approximation)

To mix hex `A` with white at `p%` (p = anchor percentage):
```
R = round(R_A * p/100 + 255 * (1 - p/100))
G = round(G_A * p/100 + 255 * (1 - p/100))
B = round(B_A * p/100 + 255 * (1 - p/100))
```

To mix hex `A` with black at `q%` (q = black percentage):
```
R = round(R_A * (1 - q/100))
G = round(G_A * (1 - q/100))
B = round(B_A * (1 - q/100))
```
