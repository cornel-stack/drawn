# CLAUDE.md — house rules for `drawn`

`drawn` turns text lesson files into hand-drawn-style educational YouTube videos
for three channels: **Chalk & Vector** (`chalk-and-vector`, university maths),
**Pen & Pendulum** (`pen-and-pendulum`, calculus-based physics), and
**Marginal Ink** (`marginal-ink`, university economics).

Everything is free and open source. It runs on an Ubuntu laptop and, later, in
GitHub Actions on a public repo. No paid APIs, no cloud storage, no YouTube API.

## How a lesson gets written (scriptwriting rules)

- Read the backlog row (`channels/<name>/backlog.yaml`) and the cited open
  textbook section (OpenStax or other CC BY / CC BY-SA). Understand it, then
  **explain in our own words — never copy sentences** from the source.
- Derivations are **step by step**: every step is written on the board at the
  moment it is spoken.
- **British spelling** throughout (colour, behaviour, generalise, …).
- No hype. No "in this video", no "hey guys", no calls to subscribe.
- End every lesson with a **one-line summary** and the **next lesson's code**.
- Narration is plain prose at **~140–150 words per minute** of target length.
  The linter enforces the total word budget to within ±15%.

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
- **Nothing static > 3 s.** The render engine fills every gap with motion (3D
  camera drift, continued primitive motion, or a gentle pulse of the active 2D
  item) and pads the tail the same way — never a frozen frame. So the only real
  pacing risk is a long lead-in (above).
- **Colour discipline.** One accent per quantity across the whole lesson; a
  formula's sub-parts match the diagram via `tex_colors`. Base ink is white on
  the black board; `palette`/`accents` entries are accent colours only.
- **Composition.** Diagram scenes carry their formula/label at the **top**; the
  diagram fills the rest. Keep at most ~4 formula or ~6 text lines on screen.

### Word budget in practice

The linter enforces `target_minutes × 145` words, ±15 %. But **Kokoro speaks at
~175 wpm, not 145**, so a 7-minute lesson (≈ 1015-word budget) renders to about
5:50 of audio. Write to the **upper half** of the band to land near the target
length; LA-01/ME-01 came in ~860–910 words (7 min) and MI-01 ~1120 (9 min).

### Pronunciation (`channels/<name>/pronounce.yaml`)

A `map:` of symbol/term → spoken form, applied to both `say` fields and the
narration before synthesis (e.g. `"\\omega": "omega"`, `"\\times": "cross"`,
`"ceteris paribus": "keteris paribus"`). Longest match wins; alphabetic terms
are word-bounded. Still write every `say` in plain spoken words — the map is the
safety net and the place to fix whatever the voice mangles. The linter **warns**
about any speakable LaTeX symbol (Greek letters, operators) used with no entry,
so keep each channel's map complete as new symbols appear.

## Engineering rules

- **Pin versions.** Python via uv (`uv.lock` committed), Node 22 LTS (`.nvmrc`
  + `engines`), pnpm lockfile committed. CI uses the pinned `manimcommunity/manim`
  Docker image by digest so TeX Live is not reinstalled every run.
- **Never commit `out/` or `.cache/`** (nor `media/`, `node_modules/`, `.venv/`).
- **Every stage is idempotent and resumable.** `packages/cache` keys each stage
  on a content hash (lesson snippet + code + voice settings); unchanged inputs
  skip re-render.
- **Tests** cover the schema and the linter. A **demo lesson** (`ME-25`) renders
  in **under 5 minutes** on a laptop at preview quality (480p15).
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
`just lint | tts | render | preview | build | fetch | new-lesson | check | sheet`.

Full 1080p renders are heavy, so they run in **GitHub Actions**, not on the
laptop:

- `just render-ci <channel> <CODE>` triggers the `render` workflow (lint → tts →
  per-scene matrix → assemble → artifact).
- `just pull <channel> <CODE>` downloads that run's finished `video.mp4` (plus
  `sheet.png`, `thumbnail.png`, `meta.md`, `captions.srt`) into
  `out/<channel>/<CODE>/` so you have the video locally.

Locally, only the light stages are run: writing/editing, `just lint`, and the
lead-in/word-budget checks. Avoid running `tts`/`render` on the laptop.
