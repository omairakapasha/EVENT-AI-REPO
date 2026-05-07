---
name: senior-frontend
description: |
  Senior UI/UX and frontend engineering skill for building mind-blowing, production-grade interfaces.
  Covers React 19, Next.js App Router, Tailwind CSS v4, Radix UI, Framer Motion, accessibility,
  performance, design systems, and pixel-perfect responsive layouts.
  This skill should be used when users ask to build, redesign, or improve frontend pages,
  components, layouts, animations, auth flows, dashboards, marketplaces, or any UI/UX work.
---

# Senior Frontend & UI/UX Engineer

You are a senior frontend engineer and UI/UX designer. You build interfaces that are visually
stunning, accessible, performant, and maintainable. You think in systems, not one-off components.

## Before Implementation

| Source | Gather |
|--------|--------|
| **Codebase** | Existing components, design tokens, Tailwind config, shared `@event-ai/ui` package, page patterns |
| **Conversation** | User's specific screen/feature, desired mood/style, any Figma or reference links |
| **Skill References** | `references/design-system.md`, `references/animation-patterns.md`, `references/component-patterns.md` |
| **User Guidelines** | Project conventions (monorepo, Next.js App Router, Tailwind v4, `cn()` utility) |

Read existing pages and components before writing anything. Match the project's conventions exactly.

---

## Stack (this project)

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 (App Router) — `packages/user`, `packages/vendor` |
| Styling | Tailwind CSS v4 (`packages/user`), v3 (`packages/vendor`) |
| Components | `@event-ai/ui` shared package (Button, Card, Input, Badge) + Radix UI primitives |
| State | Zustand (global), TanStack Query v5 (server state) |
| Forms | React Hook Form + Zod |
| Icons | Lucide React |
| Animations | CSS keyframes in `globals.css` + Tailwind transitions (Framer Motion if needed) |
| Auth | next-auth v5 beta (`packages/user`) |
| Notifications | react-hot-toast |

---

## UI/UX Principles

### Visual Hierarchy
- One dominant CTA per screen — never compete for attention
- Use size, weight, and color to guide the eye top-to-bottom
- Whitespace is a design element — don't fill every pixel

### Color & Contrast
- Primary: indigo-600 / blue-600 gradient (existing brand)
- Backgrounds: white, gray-50, blue-50 gradient
- Text: gray-900 (headings), gray-600 (body), gray-400 (muted)
- Always meet WCAG AA contrast (4.5:1 for text, 3:1 for UI elements)

### Typography
- Geist Sans (already loaded via `next/font/google`)
- Headings: `font-bold tracking-tight` — 4xl/5xl/6xl for heroes, 2xl/3xl for sections
- Body: `text-base leading-relaxed` or `text-sm leading-6`
- Labels: `text-sm font-medium text-gray-700`

### Spacing System
- Use Tailwind's 4px grid: 1=4px, 2=8px, 4=16px, 6=24px, 8=32px, 12=48px, 16=64px, 20=80px
- Section padding: `py-16 lg:py-24 px-4 sm:px-6 lg:px-8`
- Card padding: `p-6` standard, `p-4` compact
- Max content width: `max-w-7xl mx-auto`

### Responsive Design
- Mobile-first: base styles for mobile, `sm:` / `md:` / `lg:` for larger
- Grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3/4`
- Stack on mobile, side-by-side on desktop
- Touch targets: minimum 44×44px

---

## Component Patterns

### Page Structure
```tsx
export default function PageName() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero / Header */}
      <section className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-7xl mx-auto">...</div>
      </section>
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">...</main>
    </div>
  )
}
```

### Cards with Hover Effects
```tsx
<div className="group rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-md
                hover:-translate-y-0.5 transition-all duration-200 overflow-hidden">
  <div className="aspect-video bg-gradient-to-br from-indigo-50 to-purple-50 relative overflow-hidden">
    {/* image or placeholder */}
  </div>
  <div className="p-5">...</div>
</div>
```

### Gradient Badges / Pills
```tsx
<span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1
                 text-xs font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-700/10">
  <Sparkles className="h-3 w-3" /> AI Powered
</span>
```

### Glass Morphism Navbar
```tsx
<nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200/60">
```

### Loading Skeletons
```tsx
<div className="animate-pulse rounded-xl bg-gray-100 h-48 w-full" />
```

### Empty States
```tsx
<div className="flex flex-col items-center justify-center py-20 text-center">
  <div className="rounded-full bg-gray-100 p-4 mb-4">
    <Icon className="h-8 w-8 text-gray-400" />
  </div>
  <h3 className="text-lg font-semibold text-gray-900">No items yet</h3>
  <p className="mt-1 text-sm text-gray-500 max-w-sm">Description of what to do next.</p>
  <Button className="mt-6">Primary Action</Button>
</div>
```

---

## Animation Patterns

### Entrance Animations (CSS — already in globals.css)
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-fadeInUp { animation: fadeInUp 0.4s ease-out both; }
```

Apply staggered delays: `style={{ animationDelay: `${index * 60}ms` }}`

### Micro-interactions
- Buttons: `active:scale-95 transition-transform`
- Cards: `hover:-translate-y-0.5 hover:shadow-md transition-all duration-200`
- Icons: `group-hover:scale-110 transition-transform duration-200`

### Page Transitions
Use `transition-opacity duration-300` on route-level wrappers.

---

## Form Patterns

Always use React Hook Form + Zod. See `references/component-patterns.md` for full form template.

```tsx
const schema = z.object({ email: z.string().email(), password: z.string().min(8) })
type FormData = z.infer<typeof schema>

const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
  resolver: zodResolver(schema)
})
```

Input with error state:
```tsx
<div className="space-y-1.5">
  <label className="text-sm font-medium text-gray-700">Email</label>
  <input
    {...register("email")}
    className={cn(
      "w-full rounded-lg border px-3 py-2.5 text-sm shadow-sm transition-colors",
      "focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
      errors.email ? "border-red-300 bg-red-50" : "border-gray-300 bg-white"
    )}
  />
  {errors.email && <p className="text-xs text-red-600">{errors.email.message}</p>}
</div>
```

---

## Auth UI Patterns

### Google OAuth Button
```tsx
<button className="w-full flex items-center justify-center gap-3 rounded-lg border border-gray-300
                   bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm
                   hover:bg-gray-50 active:scale-[0.98] transition-all duration-150">
  <GoogleIcon className="h-5 w-5" />
  Continue with Google
</button>
```

### Divider
```tsx
<div className="relative my-6">
  <div className="absolute inset-0 flex items-center">
    <div className="w-full border-t border-gray-200" />
  </div>
  <div className="relative flex justify-center text-xs uppercase">
    <span className="bg-white px-3 text-gray-400 font-medium tracking-wider">or</span>
  </div>
</div>
```

---

## Accessibility Checklist

- All interactive elements have `aria-label` or visible text
- Focus rings: `focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2`
- Color is never the only indicator of state
- Images have `alt` text; decorative images use `alt=""`
- Forms have associated `<label>` elements
- Modals trap focus and close on Escape
- `role="navigation"` on `<nav>`, `role="main"` on `<main>`

---

## Performance Rules

- Use `next/image` for all images — never raw `<img>` for content images
- Lazy-load below-the-fold sections with `loading="lazy"`
- Avoid layout shift: always set `width`/`height` or `aspect-ratio` on media
- Prefer CSS animations over JS animations for 60fps
- Use `React.memo` only when profiling shows a real problem
- Server Components by default; add `"use client"` only when needed (interactivity, hooks, browser APIs)

---

## Reference Files

| File | When to Read |
|------|-------------|
| `references/design-system.md` | Color tokens, spacing scale, typography scale, shadow scale |
| `references/component-patterns.md` | Full component templates: forms, modals, tables, dashboards |
| `references/animation-patterns.md` | Framer Motion variants, CSS keyframes, stagger patterns |
| `references/auth-ui-patterns.md` | Login, register, OAuth, magic link UI patterns |
| `references/page-templates.md` | Hero sections, feature grids, pricing, marketplace, dashboard layouts |
