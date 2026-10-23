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
`just lint | tts | render | preview | build | fetch | new-lesson`.
