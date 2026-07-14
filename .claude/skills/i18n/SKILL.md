---
name: i18n
description: Use when a code or template change introduces a new translation message key, in either the framework CLI (aegis/i18n/locales/) or a generated project's CLI (the app/i18n/locales/ template tree). Covers adding the real English string, stubbing the same key into every other locale for parity, and the separate translation PR that later replaces placeholders with reviewed native text.
---

# i18n

Adds a new i18n message key so `tests/core/test_i18n.py` (framework side) or
the generated project's own `tests/test_i18n.py` keeps passing. Both trees
share the same rule: a key that exists in English must exist, with some
value, in every other locale file, or the completeness test fails by name.

## When to use

Use when a feature or fix needs a brand-new string shown through the
translation layer (`t("some.key")` or `lazy_t("some.key")`), in either:

- The framework's own CLI (`aegis ...` commands), backed by
  `aegis/i18n/locales/`.
- A generated project's CLI (`app/i18n/locales/` under the copier template),
  which is a separate, parallel i18n tree with the same shape.

Do NOT use this skill to perform the actual translation work into
non-English languages; that is a separate, later PR (see Procedure below).
Do NOT use it for changing the wording of an existing English string without
adding a key; that is ordinary feature work, though it still needs the
placeholder value updated in every other locale if the value materially
changes (rare - most wording tweaks are English-only maintenance and do not
require this skill).

## Files that change

Framework i18n (`aegis/i18n/`):

- `aegis/i18n/locales/en.py`: canonical `MESSAGES: dict[str, str]`. Add the
  key with its real English value under the matching section-comment banner
  (e.g. `# --- Validation ---`, `# --- Interactive: AI service ---`). Keys are
  dot-separated `<area>.<name>`, matching existing groups such as
  `service.<name>`, `component.<name>`, `interactive.*`, `projectmap.*`,
  `add_service.*`, `deploy.*`.
- `aegis/i18n/locales/{de,es,fr,ja,ko,ru,zh,zh_hant}.py`: add the SAME key to
  each file, value = the English string, unmodified (a placeholder, not a
  translation).
- `aegis/i18n/locales/__init__.py`: `AVAILABLE_LOCALES` set; only touch this
  if adding a whole new locale, not a new key.
- `aegis/i18n/registry.py`: `translate()` does the lookup and fallback; no
  edit needed for a new key, it is generic over the dict.
- `tests/core/test_i18n.py`: `TestMessageCompleteness` is the gate. A missing
  key fails with a message like `Keys in en but not de: {'the.new.key'}`; an
  extra key (present in a locale but not English) fails the mirror-image
  assertion.

Generated-project i18n (a template change, see the template-dev skill for
the commit/render caveat):

- `aegis/templates/copier-aegis-project/{{ project_slug }}/app/i18n/locales/en.py`
- `aegis/templates/copier-aegis-project/{{ project_slug }}/app/i18n/locales/{de,es,fr,ja,ko,ru,zh,zh_hant}.py`
- `aegis/templates/copier-aegis-project/{{ project_slug }}/app/i18n/registry.py.jinja`:
  same fallback-chain `translate()`; no edit needed for a new key.
- `aegis/templates/copier-aegis-project/{{ project_slug }}/tests/test_i18n.py`:
  the generated project's own completeness test. It imports only `en` and
  `zh` explicitly and asserts those two key sets match; it does not loop over
  all nine locales the way the framework's test does. Stub the key into all
  eight non-English locales anyway, for consistency with the framework rule
  and to keep every locale file real (no dangling English-only keys).

## Procedure

Adding a new key:

1. Decide which tree owns the string (framework CLI vs generated-project
   CLI). If both need it independently, repeat the rest of these steps once
   per tree.
2. Write or adjust the consuming code to call `t("<area>.<name>", ...)` or
   `lazy_t("<area>.<name>", ...)` at the call site.
3. Add the key with its real English string to that tree's `en.py`, under
   the appropriate section-comment banner, following the existing
   `<area>.<name>` naming.
4. Add the same key to every other locale file in that tree, using the
   English string as the value (a placeholder, not a translation).
5. Run the gates (see Gates below) and confirm the completeness test passes.
6. If the generated-project tree changed, treat it as a template change:
   commit it (or use `aegis init --dev`) before validating with
   `make test-template`, per the template-dev skill.

Translation PR (separate flow, later):

1. Take the placeholder (English-value) entries in the non-English locale
   files and replace them with real, native translations.
2. The agent produces the initial translation pass.
3. A human translator reviews and corrects it; iterate back and forth until
   the wording reads native, not like a literal translation. Mandarin is the
   main quality bar for "does this sound native."
4. Keep phrasing compact: these are CLI strings rendered in a terminal.
   Prefer a compact, natural phrase over a longer one that is technically
   clearer; skip "clearer but longer" rewrites suggested along the way.
5. Run the same gates again; only wording changed, so the completeness test
   should already pass, but confirm no key was dropped in the edit.

## Gates

- `make check` (framework side: lint, typecheck, `tests/core/test_i18n.py`
  included in the default test run) must pass whenever
  `aegis/i18n/locales/` changed.
- `make test-template` when the generated-project locale files under
  `aegis/templates/copier-aegis-project/{{ project_slug }}/app/i18n/locales/`
  changed; this generates a project and runs its own test suite, including
  `tests/test_i18n.py`.

## Pitfalls

- Adding a key to `en.py` only fails `tests/core/test_i18n.py`, which checks
  both directions (missing keys and extra keys) for every locale, so the
  key must exist everywhere before `make check` is green.
- Do not write real translations in the same change that introduces the key;
  that is the separate translation PR's job, done with a human translator in
  the loop, not invented inline.
- Word-for-word translations read wrong to native speakers; the bar is
  natural, native phrasing, and Mandarin is where this has mattered most in
  review.
- CLI strings render in a fixed terminal width; prefer the compact phrasing
  and skip "clearer but longer" rewrites even when they read a bit better in
  isolation.
- Generated-project locale edits are template changes: Copier renders from
  the committed git state (or the working tree only under `aegis init
  --dev`), so an uncommitted edit under `app/i18n/locales/` will not show up
  in a freshly generated project until it is committed.
- The runtime fallback in `translate()` (current locale, then English, then
  the raw key) means a missing locale entry would still show something
  reasonable at runtime, but `tests/core/test_i18n.py` does not rely on
  runtime behavior; it asserts exact key-set equality, so relying on the
  fallback instead of stubbing the key still fails the gate.
- The generated project's own `tests/test_i18n.py` only compares `en` against
  `zh` by name; it will not catch a key missing from `de`, `es`, `fr`, `ja`,
  `ko`, `ru`, or `zh_hant`. Stub the key into all eight non-English locales
  regardless, since that test's narrower coverage is not a license to skip
  the others.
