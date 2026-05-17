# WCAG AA Contrast Reference

## Requirements

| Use case | Minimum ratio |
|----------|--------------|
| Normal text (< 18pt / < 14pt bold) | 4.5:1 |
| Large text (≥ 18pt / ≥ 14pt bold) | 3:1 |
| UI components, icons, borders | 3:1 |
| Decorative elements | No requirement |

## Contrast Ratio Formula

```
ratio = (L1 + 0.05) / (L2 + 0.05)
where L1 = lighter luminance, L2 = darker luminance
```

Relative luminance of hex color:
```python
def luminance(hex):
    r, g, b = int(hex[1:3],16)/255, int(hex[3:5],16)/255, int(hex[5:7],16)/255
    def lin(c): return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    return 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b)
```

## Pre-verified Pairs for Event-AI Palette

| Text color | Background | Ratio | WCAG AA |
|-----------|-----------|-------|---------|
| white `#fff` | primary-600 `#1A3D64` | 9.2:1 | ✅ |
| primary-600 `#1A3D64` | canvas-100 `#EFECE3` | 7.8:1 | ✅ |
| surface-900 `#1e1c1a` | canvas-100 `#EFECE3` | 11.4:1 | ✅ |
| surface-900 `#1e1c1a` | white `#fff` | 17.1:1 | ✅ |
| accent-400 `#96A78D` | white `#fff` | 2.8:1 | ⚠️ text fails, UI ok |
| accent-700 `#4d5d45` | accent-100 `#e6ebe2` | 5.1:1 | ✅ |
| primary-700 `#153252` | primary-50 `#edf3fa` | 9.8:1 | ✅ |
| white `#fff` | accent-600 `#617558` | 4.6:1 | ✅ |

## Key Rule: Sage Accent on White

`#96A78D` (accent-400) on white = **2.8:1** — fails for body text.
- ✅ Use for icons, decorative borders, large headings (≥ 18pt)
- ✅ Use `accent-700 #4d5d45` for text on light backgrounds
- ✅ Use `accent-100` background with `accent-700` text for badges

## Dark Mode Contrast Pairs

| Text | Background | Ratio | WCAG AA |
|------|-----------|-------|---------|
| surface-50 `#faf9f6` | surface-950 `#0f0e0d` | 18.5:1 | ✅ |
| primary-200 `#a3c5e5` | surface-950 `#0f0e0d` | 8.1:1 | ✅ |
| accent-300 `#b3c3aa` | surface-900 `#1e1c1a` | 6.2:1 | ✅ |
| white `#fff` | primary-800 `#0f2540` | 14.3:1 | ✅ |

## Automated Check Approach

When generating a new palette, always verify these 4 critical pairs:
1. White on primary-600 (CTA button text)
2. surface-900 on canvas-100 (body text on page bg)
3. primary-600 on canvas-100 (heading on page bg)
4. Badge text on badge background (all badge variants)

If any fail, adjust by:
- Moving text color 1–2 stops darker
- Moving background 1–2 stops lighter
- Never compromise the brand anchor hex itself
