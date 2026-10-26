# CLAUDE.md — house rules for `drawn`

`drawn` turns text lesson files into hand-drawn-style educational YouTube videos
for three channels: **Chalk & Vector** (`chalk-and-vector`, university maths),
**Pen & Pendulum** (`pen-and-pendulum`, calculus-based physics), and
**Marginal Ink** (`marginal-ink`, university economics).

Everything is free and open source. It runs on an Ubuntu laptop and, later, in
GitHub Actions on a public repo. No paid APIs, no cloud storage, no YouTube API.

## How a lesson gets written (scriptwriting rules)

- Read the backlog row (`channels/<name>/backlog.yaml`) and the cited open
  textbook section (downloaded by `just sources` into `sources/text/…`).
  Understand it, then **explain in our own words — never copy sentences** from
  the source. Record `source.book`/`section`/`license` and, when you worked from
  an extracted file, `source.file` + `source.pages`.
- Derivations are **step by step**: every step is written on the board at the
  moment it is spoken, and never two equations back-to-back with no narration
  between them.
- **British spelling** throughout (colour, behaviour, generalise, …).
- **Declarative and precise, no hype.** Define every term the first time it
  appears. The banned-phrase list is a hard linter error: no "imagine", "journey",
  "story", "magic(al)", "dive in", "in this video", "hey guys", "buckle up",
  "mind-blowing", "awesome", "amazing". Rhetorical questions are discouraged —
  the linter warns when a scene has more than one "?".
- End every lesson with a **one-line summary** and a pointer to the next lesson
  **by its title** ("Next: …"). **Never speak a lesson code** in narration — the
  code is metadata and lives only in `meta.md`.
- Narration is plain prose; the linter enforces a **runtime estimate** (words at
  the per-kind wpm + explicit pauses + equation holds) within ±15 % of
  `target_minutes` — not a raw word count. Explainer prose ≈ 140 wpm; derivation
  and problem scenes ≈ 125 wpm.

### The lesson contract

One YAML file per video at `channels/<name>/lessons/<CODE>.yaml`, validated by
`packages/schema`. Board items are referenced inline in the narration as
`{id}` placeholders:

- Each board item has an `id`. The narration writes `{id}` where the item
  should be drawn, e.g. `"angular momentum, {L}, points along the axis"`.
- Before synthesis, TTS substitutes `{id}` with the item's `say` text (text
  items without a `say` substitute to nothing). The write-start time of each
  item is the timestamp of its first substituted word after whisper alignment.
- Every `latex` item must have a `say`. Every `{id}` must resolve to an item in
  the same scene, and every item must be referenced exactly once.
- Two control tokens live in the narration alongside `{id}`: `{pause:N}` inserts
  N seconds of silence, and `{hl:id}` re-emphasises an already-drawn item
  (`Indicate` in its colour) as you refer back to it. Neither is a board item.

### Scene kinds

- `title` / `end` are **full-frame cards**: black board, the lesson title large
  in Kalam, the channel name small, held a few seconds, then cleared. They take
  **no `animation`** and are never drawn over. Keep their narration to a short
  spoken hook (or leave it silent). The opening content — prerequisites, the
  first definition — belongs in the first real scene, not on the title card.
- `derivation` writes steps; `diagram` runs a primitive; `problem` is a worked
  example (see below). `explainer`/`board` carry prose and formulas.

### Teaching *through* the formulas

A formula is never dropped on the board bare. Each equation item gets:

- a **symbol legend** (`legend:` — `sym`, `name`, `unit`) revealed beside it, so
  every symbol's meaning and units are on screen;
- narration that **states what the equation claims** in words, not just its name;
- where it helps, a concrete or limiting case ("when ω is large, Ω is small").

Use `{hl:id}` to light up a term exactly when the narration refers to it. State
the lesson's prerequisites in the first twenty seconds.

### Worked problems (`kind: problem`)

Every explainer carries **at least one** worked problem; a "derivation + worked
problem" lesson carries two. A problem scene has board items with `role:`
`statement`, `given`, `find`, `step`, `answer` (the boxed result sets
`box: true`), and a **`check:` block** that recomputes the answer in plain Python
(`expr`, `value`, `unit`, `tol`, default 1 %). The linter evaluates `check.expr`
and fails if it disagrees with the boxed `value`. Adapt problems from the source
with the numbers changed — never copy them verbatim.

### Writing a lesson in practice (learned from LA-01, ME-01, MI-01)

- **Pick the primitive first.** Each diagram scene runs one animation primitive
  (`vectors`, `vectors3d`, `axes_plot`, `supply_demand`, `gyroscope`, `wheel`)
  or a per-lesson `custom:` class in `lessons/<CODE>.py`. When a lesson needs a
  primitive that is still a stub, build it **fully** — it is reused by dozens of
  lessons. Every non-end scene carries an `animation` block except `derivation`,
  where the hand writing the steps is itself the motion.
- **Draw before you operate.** A step that uses something (`components`,
  `dot_product`, `cross`, `add_tip_to_tail`, `shift`, `intersect`) must appear
  in the narration *after* the `draw`/`plot` step that created it, or it fails at
  render (e.g. `KeyError`). Order the `{id}`s accordingly.
- **First `{id}` within ~3 s.** The pacing check fails a 2D scene whose first
  visual is more than 3 s into the narration (≈ 8 spoken words). Open every
  diagram scene with a draw/plot placeholder.
- **Nothing static > 3 s — except a deliberate read-hold.** The render engine
  fills every gap with motion (3D camera drift, continued primitive motion, or a
  gentle pulse of the active 2D item) and pads the tail the same way. The one
  exception is reading time right after an equation: each equation item
  automatically gets ≥1.2 s of silence before it is written and ≥1.0 s after, and
  the render holds that gap static (up to ~2.5 s) so the viewer can read. These
  auto-holds apply to **equation items only**, not to legends or short labels.
  Add more breathing room explicitly with `{pause:N}`.
- **Colour discipline.** One accent per quantity across the whole lesson; a
  formula's sub-parts match the diagram via `tex_colors`. Base ink is white on
  the black board; `palette`/`accents` entries are accent colours only.
- **Composition.** Diagram scenes carry their formula/label at the **top**; the
  diagram fills the rest. Keep at most ~4 formula or ~6 text lines on screen.

### Runtime budget in practice

The linter's runtime estimate counts explicit `{pause:N}` and the per-equation
auto-holds, so a derivation-heavy lesson needs **fewer words** than word-count
alone suggests. **Kokoro also speaks at ~175 wpm, not the 140 the estimate
assumes**, so write to the upper half of the band to land near the target
length. Check the estimate with `just lint` and the real gaps with `just check`
(the static-gap pass, after `just tts`).

### Sources and fact-checking

- `just sources` downloads every open textbook in `sources/manifest.yaml`
  (sha256-pinned) and extracts per-section text into `sources/text/<book>/`.
  PDFs and text are gitignored; only the manifest (with its pins) is committed.
  CI runs it too, caching PDFs by hash.
- Before a lesson may render, it needs a **complete fact-check review**:
  `just factcheck <ch> <CODE>` scaffolds `lessons/<CODE>.review.md`. Fill it with
  **evidence, not ticks** — the quoted source line with its page/equation number
  for every formula, and the actual Python recomputation with its printed output
  for every number. Set every verdict to `ok` and `status: complete`. `just
  render` runs `factcheck-gate` first and **refuses** until the review is
  complete; the gate re-runs every `check:` block itself. Do the fact-check as a
  separate pass (a subagent reading the source), not while drafting.

### Pronunciation (`channels/<name>/pronounce.yaml`)

A `map:` of symbol/term → spoken form, applied to both `say` fields and the
narration before synthesis (e.g. `"\\omega": "omega"`, `"\\times": "cross"`,
`"Coulomb": "koo-lom"`, `"Euler": "oiler"`, `"ceteris paribus": "keteris
paribus"`). Longest match wins; alphabetic terms are word-bounded. Still write
every `say` in plain spoken words — the map is the safety net. The linter
**warns** about any speakable LaTeX symbol (Greek letter, operator) or
non-sentence-initial proper noun used with no entry, so keep each channel's map
complete. Hear the whole map read aloud with `just pronounce-check <channel>`.

## Engineering rules

- **Pin versions.** Python via uv (`uv.lock` committed), Node 22 LTS (`.nvmrc`
  + `engines`), pnpm lockfile committed. CI uses the pinned `manimcommunity/manim`
  Docker image by digest so TeX Live is not reinstalled every run.
- **Never commit `out/` or `.cache/`** (nor `media/`, `node_modules/`, `.venv/`).
- **Every stage is idempotent and resumable.** `packages/cache` keys each stage
  on a content hash (lesson snippet + code + voice settings); unchanged inputs
  skip re-render.
- **Tests** cover the schema, the linter, the TTS segment timing, the sources
  manifest and the fact-check gate. Rendering is exercised end-to-end in CI, not
  on the laptop.
- Shared code is channel-agnostic; per-channel palette, board colour, font and
  voice live in `channels/<name>/channel.yaml`.

## Rendering notes

- **Formulas** are `MathTex` (standard LaTeX) animated with `Write()` + a slight
  path wobble, with the hand following the pen tip. They do **not** go through
  the handwriting font.
- **Prose / titles / labels** use Manim `Text` with the handwriting TTF (Kalam,
  vendored in `assets/fonts/` with its OFL licence) registered via `manimpango`.
- Output is **1920×1080 at 30 fps** (not 60 — render time matters). Preview is
  480p15. Audio is normalised to **−14 LUFS**.
- The hand is a placeholder transparent PNG; swapping in a real hand photo must
  be a one-file change (`assets/hand/`).

## Task runner

`just` drives everything; the same recipes run locally and in CI:
`just lint | sources | factcheck | tts | pronounce-check | check | render |
preview | build | fetch | new-lesson | sheet`. `just render` is gated on a
complete fact-check review (`factcheck-gate`) before it synthesises anything.

Full 1080p renders are heavy, so they run in **GitHub Actions**, not on the
laptop:

- `just render-ci <channel> <CODE>` triggers the `render` workflow (lint → tts →
  per-scene matrix → assemble → artifact).
- `just pull <channel> <CODE>` downloads that run's finished `video.mp4` (plus
  `sheet.png`, `thumbnail.png`, `meta.md`, `captions.srt`) into
  `out/<channel>/<CODE>/` so you have the video locally.

Locally, only the light stages are run: writing/editing, `just lint`, `just
sources`, `just factcheck`, and `just check`. Avoid running `tts`/`render` on
the laptop — synthesis and 1080p render happen in CI. To verify a lesson as you
go, trigger a **preview** render in CI (480p15) and `just pull` the sheet;
reserve the single 1080p30 render for the end.
