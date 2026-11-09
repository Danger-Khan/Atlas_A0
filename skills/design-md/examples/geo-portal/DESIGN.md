Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# DESIGN.md: Geo Risk Portal (example)

An original example design system for a calm, data-dense geospatial risk dashboard
(maps, risk badges, evidence tables). It is not copied from any brand.

## 1. Visual theme & atmosphere

Quiet, evidence-first, institutional. The map is the hero; chrome stays out of the way.
Light surfaces, one deep teal brand colour, and a three-step risk ramp that is the only
place saturated colour appears. Nothing decorative: no gradients, no glass effects, no
illustration. Density is high but never cramped; every number has a label and a unit.

## 2. Color palette & roles

| Role | Token | Use |
|---|---|---|
| Page background | `color.bg` | App canvas behind panels |
| Panel | `color.surface` | Cards, side panels, tables |
| Hairline | `color.border` | Dividers, table rules, input borders |
| Text | `color.text` | Body and headings |
| Muted text | `color.text-muted` | Captions, units, helper text |
| Brand | `color.primary` | Links, primary buttons, selected state |
| Risk | `color.risk-low`, `color.risk-medium`, `color.risk-high` | Map classes and badges only |

```design-tokens
// Surfaces
color.bg = #F4F7F8
color.surface = #FFFFFF
color.border = #D3DDE1
// Text
color.text = #13242B
color.text-muted = #4A5E68
// Brand
color.primary = #0B6674
color.primary-contrast = #FFFFFF
// Risk ramp (maps and badges only)
color.risk-low = #2E7D4F
color.risk-medium = #F2C14E
color.risk-high = #B3261E

// Typography
font.sans = Source Sans 3, system-ui, sans-serif
font.mono = IBM Plex Mono, ui-monospace, monospace

// Spacing and shape (px)
space.base = 4
radius.sm = 4
radius.md = 8
radius.lg = 12

// Contrast pairs that must always pass (WCAG 2.x AA, 4.5:1 unless stated)
pair = color.text on color.bg
pair = color.text on color.surface
pair = color.text-muted on color.surface
pair = color.primary on color.surface
pair = color.primary-contrast on color.primary
pair = color.surface on color.risk-low
pair = color.text on color.risk-medium
pair = color.surface on color.risk-high
```

## 3. Typography

- Family: `font.sans` for everything; `font.mono` only for coordinates, IDs and code.
- Scale (px / line-height): caption 13/18, body 16/24, label 14/20, h3 20/28, h2 24/32, h1 32/40.
- Weights: 400 body, 600 labels and headings. No italics for emphasis; use weight.
- Numbers in tables use tabular figures and are right-aligned with their unit in the header.

## 4. Component styling

- **Panel**: `color.surface`, 1px `color.border`, `radius.md`, 16px padding, no shadow at rest.
- **Primary button**: `color.primary` fill, `color.primary-contrast` text, `radius.sm`, 8px 16px padding, 40px tall.
- **Secondary button**: transparent, 1px `color.primary` border and text.
- **Risk badge**: pill, risk colour fill, text from the matching pair (white on low and high, dark on medium), 4px 8px padding.
- **Table**: no zebra stripes, 1px `color.border` row rules, header in `color.text-muted` at label size.
- **Map legend**: always shows all three risk classes with their numeric thresholds.

## 5. Layout principles & spacing

- Everything snaps to a 4px grid (`space.base`); preferred steps are 4, 8, 12, 16, 24, 32, 48.
- App shell: 320px side panel, fluid map, 56px top bar. Content max width 1280px outside the map.
- Group related controls with 8px gaps, separate groups with 24px.
- Align to a baseline; never centre long text blocks.

## 6. Depth & elevation

Flat by default. Only floating UI lifts: popovers and map tooltips use
`0 4px 16px rgba(19, 36, 43, 0.16)`; modals add a 40% scrim of `color.text`. Nothing else casts a shadow.

## 7. Do's and don'ts

- Do use risk colours only for risk data, so colour always carries meaning.
- Do pair every colour cue with a text label or icon (colour-blind safe).
- Do state units and data dates next to every figure.
- Do keep one primary action per view.
- Don't add colours that are not in the token block; extend DESIGN.md first.
- Don't use gradients, glows, emoji or decorative illustration.
- Don't set text smaller than 13px or lighter than `color.text-muted`.
- Don't use red or green alone to signal state.

## 8. Responsive behavior

- Breakpoints: 640px (phone to tablet), 1024px (tablet to desktop).
- Below 1024px the side panel becomes a bottom sheet; below 640px tables become stacked label/value rows.
- Touch targets are at least 44px tall; the map keeps pinch-zoom and never captures page scroll.

## 9. Agent prompt guide

Build every screen from the tokens above. Quick brief: light, flat, teal-and-slate, the map
is the hero, risk colours only for risk. Define the tokens once as CSS variables in `:root`
(for example `--color-bg`) and reference variables everywhere; never write a raw hex, font
name or off-grid pixel value in a component. After each change run `lint_design.py` and
`check_adherence.py` and fix what they report.
