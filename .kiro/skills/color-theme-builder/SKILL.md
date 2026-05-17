---
name: color-theme-builder
description: |
  Generates a complete, production-ready color theme for Next.js + Tailwind CSS projects from 1–3 brand hex codes.
  Produces full 50–950 color scales, semantic CSS custom properties, dark mode tokens, WCAG AA contrast verification,
  and writes the correct output format per Tailwind version (v3 tailwind.config.js or v4 @theme in globals.css).
  This skill should be used when users want to apply a brand palette, create a design system, switch themes,
  or generate color tokens from hex codes for any web project.
---

# Color Theme Builder

Transforms brand hex codes into a complete, accessible design token system for Tailwind CSS projects.

## Before Implementation

| Source | Gather |
|--------|--------|
| **Codebase** | Tailwind version (v3 vs v4), existing `tailwind.config.js`, `globals.css`, portal structure |
| **Conversation** | Brand hex codes (1–3), role of each color (primary/accent/background), dark mode needed? |
| **Skill References** | `references/scale-generation.md`, `references/semantic-tokens.md`, `references/wcag.md` |
| **User Guidelines** | Monorepo structure, which packages to update, existing component class names |

---

## Workflow

### Step 1 — Identify inputs

Collect from user:
- **Hex codes** (1–3): e.g. `#1A3D64`, `#96A78D`, `#EFECE3`
- **Roles**: Which is primary (CTA/headings), accent (highlights), canvas (backgrounds)?
- **Packages**: Which portals to update (vendor/user/admin)?

If roles are ambiguous, assign by luminance:
- Darkest → `primary` (navy, deep tones → CTAs, headings)
- Mid-tone → `accent` (sage, teal, coral → badges, icons, highlights)
- Lightest → `canvas` (cream, off-white → page/card backgrounds)

### Step 2 — Generate color scales

For each anchor hex, derive a full 50–950 scale using the rules in `references/scale-generation.md`.

**Quick formula:**
- 50: mix anchor with white at 5% anchor
- 100: mix at 15%
- 200: mix at 30%
- 300: mix at 50%
- 400: mix at 70%
- **500/600: anchor zone** (anchor sits at 400–600 depending on luminance)
- 700: darken anchor 15%
- 800: darken anchor 30%
- 900: darken anchor 50%
- 950: darken anchor 65%

Dark anchors (luminance < 0.25) → anchor at 600–700
Mid anchors (luminance 0.25–0.60) → anchor at 400–500
Light anchors (luminance > 0.60) → anchor at 100–200

### Step 3 — Build semantic tokens

Map scale stops to semantic roles (see `references/semantic-tokens.md`):

```
--color-bg-page        → canvas-100
--color-bg-card        → white / canvas-50
--color-bg-sidebar     → primary-600
--color-text-primary   → surface-900
--color-text-muted     → surface-500
--color-border         → canvas-200 / surface-200
--color-cta            → primary-600
--color-cta-hover      → primary-700
--color-highlight      → accent-400
```

Dark mode counterparts:
```
--color-bg-page (dark)     → surface-950
--color-bg-card (dark)     → surface-900
--color-text-primary (dark)→ surface-50
--color-border (dark)      → surface-800
```

### Step 4 — Verify WCAG AA contrast

Check every text-on-background pair (see `references/wcag.md`):
- Normal text: ≥ 4.5:1
- Large text / UI elements: ≥ 3:1

Critical pairs to always verify:
| Text | Background | Required |
|------|-----------|----------|
| `primary-600` on `canvas-100` | ≥ 4.5:1 |
| white on `primary-600` | ≥ 4.5:1 |
| `surface-900` on `canvas-100` | ≥ 4.5:1 |
| `accent-400` on white | ≥ 3:1 (UI element) |

If a pair fails, shift the text color one stop darker or the background one stop lighter until it passes.

### Step 5 — Write output

**Tailwind v3** (has `tailwind.config.js`):
- Add scales to `theme.extend.colors` in `tailwind.config.js`
- Add CSS variables + component classes to `globals.css`

**Tailwind v4** (uses `@import "tailwindcss"` in globals.css):
- Add all scales inside `@theme { }` block in `globals.css`
- Add `:root` CSS variables for semantic tokens
- No `tailwind.config.js` changes needed

**Always include in globals.css:**
- `:root` semantic token variables
- `.dark` overrides
- Component utility classes (`.btn-primary`, `.card`, `.badge-*`, `.nav-item`)
- Toast variables (`--toast-bg`, `--toast-color`)

### Step 6 — Update all target packages

Apply to each portal specified. Each portal may have a different Tailwind version — check `package.json` before writing.

---

## Output Format

For each package updated, confirm:
```
✅ packages/vendor/tailwind.config.js  — primary, accent, canvas, surface scales added
✅ packages/vendor/src/app/globals.css — CSS vars + component classes updated
✅ packages/user/src/app/globals.css   — @theme tokens + semantic vars updated
✅ packages/admin/src/app/globals.css  — @theme tokens + admin sidebar vars updated
```

Then show the palette summary:

```
Brand Palette Applied
─────────────────────────────────────────
primary  #1A3D64  → navy   (CTAs, headings, sidebar)
accent   #96A78D  → sage   (badges, icons, highlights)
canvas   #EFECE3  → cream  (page bg, card bg)
surface  derived  → warm neutral (text, borders)

WCAG AA ✅
  white on primary-600 (#1A3D64)  → 9.2:1
  surface-900 on canvas-100       → 11.4:1
  primary-600 on canvas-100       → 7.8:1
```

---

## Rules

- Never use cold zinc/gray neutrals when a warm canvas color is provided — derive warm-tinted surface scale instead
- Always keep `success`, `warning`, `error` scales unchanged (functional colors must stay recognizable)
- `refetchOnWindowFocus` and other non-theme settings are out of scope — don't touch them
- Preserve all existing animation keyframes and font imports
- Component classes (`.btn`, `.card`, `.badge`) must be updated to use new token names, not hardcoded hex
- In v4, never write color tokens in `tailwind.config.js` — use `@theme` only
- In v3, never use `@theme` — use `theme.extend.colors` only
