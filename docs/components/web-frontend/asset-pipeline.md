# Asset Pipeline

The web frontend fingerprints its assets with a small, dependency-free
pipeline instead of a bundler: content-hash each file, copy it to a hashed
name, write a manifest, and let templates resolve through it.

```
   static/css/app.css ─┐
   static/js/*.js      ├── build.py ──> static/dist/css/app-42a20433.css
   static/dist/app.css ┘        │       static/dist/js/app-a7fcf322.js
    (Tailwind output)           │       static/dist/app-ddc209d0.css
                                └─────> static/dist/manifest.json
```

## static(): how templates reference assets

Templates never hardcode asset URLs. They call the `static()` global:

```html
<link rel="stylesheet" href="{{ static('css/app.css') }}">
```

`static()` looks the logical path up in `static/dist/manifest.json`:

- **Manifest has it**: returns the hashed URL,
  `/static/dist/css/app-42a20433.css`.
- **No manifest, or the path is not in it**: returns the plain source URL,
  `/static/css/app.css`.

Both URLs serve correctly. The fallback is what makes development buildless:
a fresh project renders pages before `npm install` has ever run. The manifest
is re-read whenever its mtime changes, so a rebuild is picked up on the next
render with no server restart.

## Cache policy

Assets are served by `CachedStaticFiles`, which applies a two-tier
`Cache-Control` policy:

| Asset | Policy | Why it is safe |
|---|---|---|
| Fingerprinted (`app-42a20433.css`) | `max-age=31536000, immutable` | The URL changes whenever the content does, so the browser never needs to revalidate. |
| Everything else | `max-age=3600` | One hour fresh, then a conditional request returns 304. |

Worst-case staleness for unhashed assets is one hour after a deploy. For
fingerprinted assets it is zero, because the HTML points at the new hash the
moment it deploys.

## Running the pipeline

```bash
make build-static
```

That compiles Tailwind (`npm run build`) and then fingerprints
(`python -m app.components.web_frontend.build`), in that order; hashing first
would fingerprint the previous stylesheet.

`build.py` discovers its sources by globbing `static/css/`, `static/js/`, and
the Tailwind output `static/dist/app.css`. There is no source list to
maintain: drop a new JS file into `static/js/` and it is fingerprinted on the
next build. The build is idempotent, and everything under `static/dist/` is
gitignored; production images bake it at build time instead.

## The dev loop

`make serve` runs two extra dev-only compose services for htmx projects:

```
   edit a template or static/js file
        │
        ▼
   tailwind (node:22-alpine) ── rewrites ──> static/dist/app.css
        │                                        │
        │                                        ▼
        │                     build-static-watcher ── rewrites ──> manifest.json
        │                                                              │
        ▼                                                              ▼
   browser refresh: static() reads the new manifest, serves new CSS
```

- **`tailwind`** runs the Tailwind CLI in watch mode. It polls the filesystem
  (`CHOKIDAR_USEPOLLING`) because Docker bind mounts do not deliver file
  events on macOS or Windows.
- **`build-static-watcher`** reuses the webserver image and runs
  `build_watch.py`, which re-fingerprints whenever a source changes. It
  debounces bursts of writes and deliberately ignores its own output;
  without that filter, each rebuild would trigger the next one forever.

The result: edit a Tailwind class in a template, refresh the browser, see the
new style. No server restart, no manual build.

## Production images

The Dockerfile has a `css-build` stage (`node:22-alpine`) that installs the
npm dev dependencies, compiles Tailwind, and hands the result to the runtime
stage, which fingerprints it once at image build:

```
FROM node:22-alpine AS css-build     # npm install + tailwindcss --minify
FROM python:...                      # runtime
COPY --from=css-build .../dist/app.css ...
RUN python -m app.components.web_frontend.build
```

Node and npm never exist in the runtime layer. The shipped image serves
fingerprinted, immutable-cached CSS with no build tooling inside it.
