# Styling and Theming

## Precompiled, never CDN

Tailwind is compiled ahead of time into `static/dist/app.css`. There is no
runtime JIT and no CDN script tag. The visual result is identical; the
difference is that classes Tailwind cannot see fail loudly in development
instead of silently in production, and pages ship one minified stylesheet
instead of a compiler.

```bash
npm install          # once; pulls Tailwind, DaisyUI, Biome (devDependencies only)
make build-static    # compile + fingerprint
```

In development you rarely need either: pages render without a build because
asset resolution falls back to source paths (see
[Asset pipeline](asset-pipeline.md)), and `make serve` runs a watcher that
rebuilds CSS on template changes.

!!! warning "Tailwind only emits classes it can see"
    `tailwind.config.js` scans `app/components/web_frontend/templates/**/*.html`
    and `static/js/**/*.js`. A Tailwind class anywhere else (a Python string,
    a new template directory) will not be in the compiled CSS. If you add a
    template location, add its glob to `content` in `tailwind.config.js`.

## The single rebrand point

Brand colors live in exactly one file: `tailwind.config.js`. The block is
marked in the file itself:

```js
colors: {
  aegis: {
    bg: "#090B0D",     // Page background
    card: "#111418",   // Card/surface background
    border: "#272C36", // Borders, dividers
    text: "#EEF1F4",   // Primary text
    muted: "#7E8A9A",  // Secondary/muted text
    teal: "#17CCBF",   // Brand accent
    amber: "#F59E0B",  // Warning/highlight
  },
},
```

These become utilities (`bg-aegis-bg`, `text-aegis-teal`,
`border-aegis-border`) used throughout the shipped templates. The DaisyUI
theme below the block mirrors the same values into DaisyUI's semantic slots
(`primary`, `base-100`, `success`), so component classes like `btn` and `card`
match the hand-written utilities. Change the block, rebuild, and the whole
frontend follows. Nothing else hardcodes a hex value.

The theme is selected in `base.html` via `data-theme="aegis"` on the `<html>`
element.

## The layers

Three places styling can live, in order of preference:

1. **Utility classes in templates.** The default. Most of the shipped markup
   is plain Tailwind utilities.
2. **`static/input.css`, `@layer components`.** For a pattern that repeats
   across templates when a Jinja macro would be overkill:

    ```css
    @layer components {
      .card-surface {
        @apply bg-aegis-card border border-aegis-border rounded-lg;
      }
    }
    ```

    Utilities are emitted after this layer, so a call site can still override
    a component class.

3. **`static/css/app.css`.** Hand-authored CSS that is not Tailwind at all.
   It ships with two rules worth knowing about: `[x-cloak]{display:none}`
   (hides elements until Alpine initializes them, preventing a flash of
   unstyled content on htmx swaps) and `color-scheme: dark` (tells the
   browser to render native controls dark).

## Linting

`make lint-frontend` runs [Biome](https://biomejs.dev/) over
`static/js/` and [djlint](https://djlint.com/) over the templates. Both are
scoped to the web frontend; neither touches the rest of the project. djlint
runs with the Jinja profile and a small, documented ignore list in
`pyproject.toml` (`[tool.djlint]`). `make format-frontend` reflows the JS with
Biome; it is opt-in because reformatting is noisy in diffs.
