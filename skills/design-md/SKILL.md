---
name: design-md
description: Create, apply and verify a DESIGN.md (a machine-checkable design system spec) for any UI work. Use when building or restyling a frontend, when a project has a DESIGN.md, or when asked to make an interface consistent, on-brand, accessible or less generic.
---
Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# design-md: build UI from a DESIGN.md and prove it followed it

A `DESIGN.md` is a plain-markdown design system that lives in the project root. It has nine
sections plus one machine-readable ```design-tokens``` block. This skill makes the agent
read it before writing UI, build only from its tokens, and then check its own work with two
scripts instead of claiming it looks right.

Paths below assume the skill is installed at `.claude/skills/design-md/`. Run commands from
the project root. Python 3.8+, no packages needed.

## Workflow

1. **Find the spec.** Look for `DESIGN.md` in the project root.
   - Present: read all of it before touching UI.
   - Missing and the project already has styles: run
     `python .claude/skills/design-md/tools/extract_tokens.py src` and use the output as a
     starting block. Name colours by role (bg, surface, text, primary), then fill the template.
   - Missing and the project is new: copy `templates/DESIGN.template.md` to `DESIGN.md`, ask the
     user for mood, audience, one or two reference sites and any brand colours, then fill it in.
     Do not invent a brand identity silently.
2. **Lint the spec** before using it:
   `python .claude/skills/design-md/tools/lint_design.py DESIGN.md`
   Fix errors first (missing sections, bad hex, failing contrast pairs). Warnings such as TODO
   placeholders should be resolved or reported.
3. **Build from tokens only.**
   - Declare every token once as a CSS variable in `:root` (or the framework's theme file),
     for example `--color-bg`, `--font-sans`, `--space-2`.
   - Components reference variables. No raw hex, rgb(), font name or off-grid pixel value
     inside a component.
   - Spacing is a multiple of `space.base`; radii come from `radius.*`.
   - Follow the sections for components, layout, elevation, responsive behavior and the
     do's and don'ts, not just the colours.
4. **Verify.** After every UI change:
   `python .claude/skills/design-md/tools/check_adherence.py src --design DESIGN.md`
   Errors (unknown colours or fonts) must be fixed. Warnings (off-grid spacing, unknown radii)
   are fixed unless there is a stated reason. If the scan flags a false positive, pass
   `--allow-color` or `--allow-font` and say so in the summary.
5. **Report honestly.** Tell the user the lint result, the adherence result, and anything you
   allowed or could not check. The tools do not look at the rendered page; for a visual check,
   open it in a browser and screenshot it.

## Changing the design system

Editing a token or adding a colour is a design decision. Edit `DESIGN.md` first, say what changed
and why, re-run `lint_design.py`, then update the code. Never add a one-off colour to a component
to "make it work".

## Rules

- Contrast pairs in the token block are the accessibility contract; do not weaken a ratio to make
  a lint pass. Pick a different colour.
- A DESIGN.md that describes a real company's site is inspiration, not a template to copy. For
  anything public, derive your own palette, type and components rather than reproducing a brand.
- Colour must not be the only signal; pair it with text or an icon (see the do's and don'ts).
- Do not edit `tools/` or `tests/` to make a check pass. If a check is wrong, tell the user.

## Files

- `tools/lint_design.py`: required sections, token validity, WCAG contrast of declared pairs.
- `tools/check_adherence.py`: scans source for colours, fonts, spacing and radii outside the spec.
- `tools/extract_tokens.py`: proposes a token block from existing code.
- `templates/DESIGN.template.md`: blank spec with all sections.
- `examples/geo-portal/`: a worked, original example with passing and failing sample sites.
- `evidence/`: recorded outputs proving the tools behave as documented (see `EVIDENCE.md`).
- `README.md`: install, format reference, CI usage, limits.
