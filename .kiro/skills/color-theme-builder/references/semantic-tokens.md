# Semantic Token Mapping

## Token Layers

```
Brand hex codes
    ↓
Color scales (50–950)
    ↓
Semantic tokens (--color-bg-page, --color-cta, etc.)
    ↓
Component classes (.btn-primary, .card, .badge-accent)
```

## Standard Semantic Token Set

### Backgrounds
| Token | Light value | Dark value |
|-------|-------------|------------|
| `--color-bg-page` | canvas-100 | surface-950 |
| `--color-bg-card` | white | surface-900 |
| `--color-bg-card-tinted` | canvas-50 | surface-900 |
| `--color-bg-sidebar` | primary-600 | primary-800 |
| `--color-bg-input` | white | surface-900 |
| `--color-bg-hover` | canvas-100 | surface-800 |
| `--color-bg-active` | primary-50 | primary-950 |

### Text
| Token | Light value | Dark value |
|-------|-------------|------------|
| `--color-text-primary` | surface-900 | surface-50 |
| `--color-text-secondary` | surface-600 | surface-400 |
| `--color-text-muted` | surface-400 | surface-500 |
| `--color-text-on-primary` | white | white |
| `--color-text-heading` | primary-600 | primary-200 |
| `--color-text-link` | primary-600 | primary-300 |

### Borders
| Token | Light value | Dark value |
|-------|-------------|------------|
| `--color-border` | canvas-200 | surface-800 |
| `--color-border-strong` | surface-300 | surface-700 |
| `--color-border-focus` | primary-500 | primary-400 |

### Interactive
| Token | Light value | Dark value |
|-------|-------------|------------|
| `--color-cta` | primary-600 | primary-500 |
| `--color-cta-hover` | primary-700 | primary-400 |
| `--color-cta-active` | primary-800 | primary-300 |
| `--color-highlight` | accent-400 | accent-400 |
| `--color-highlight-bg` | accent-100 | accent-900 |

## Component Class → Token Mapping

### Buttons
```css
.btn-primary  → bg: --color-cta, text: white, hover: --color-cta-hover
.btn-accent   → bg: accent-400, text: white, hover: accent-500
.btn-outline  → border: primary-300, text: primary-600, hover-bg: primary-50
.btn-ghost    → bg: transparent, hover-bg: --color-bg-hover
```

### Cards
```css
.card         → bg: white, border: --color-border, shadow-sm
.card-canvas  → bg: canvas-50, border: canvas-200, shadow-sm
```

### Badges
```css
.badge-primary → bg: primary-100, text: primary-700
.badge-accent  → bg: accent-100, text: accent-700
.badge-success → bg: success-100, text: success-700
.badge-warning → bg: warning-100, text: warning-700
.badge-error   → bg: error-100, text: error-700
```

### Navigation
```css
.nav-item        → text: surface-600, hover-bg: canvas-100, hover-text: primary-600
.nav-item-active → bg: primary-50, text: primary-700, font-semibold
```

## Admin-Specific Tokens

Admin portals typically use a navy sidebar. Add these extra tokens:

```css
:root {
  --sidebar-bg:      #1a3d64;   /* primary-600 */
  --sidebar-text:    #d0e2f2;   /* primary-100 */
  --sidebar-hover:   #153252;   /* primary-700 */
  --sidebar-active:  #2260a0;   /* primary-500 */
  --sidebar-border:  #0f2540;   /* primary-800 */
}
```

Admin status badges:
```css
.badge-pending    → bg: warning-100, text: warning-800
.badge-active     → bg: accent-100,  text: accent-700   (sage = approved/active)
.badge-suspended  → bg: error-100,   text: error-800
```
