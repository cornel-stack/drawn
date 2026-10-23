# drawn

Hand-drawn-style educational YouTube videos, generated from plain-text lesson
files, for three channels: **Chalk & Vector** (maths), **Pen & Pendulum**
(physics) and **Marginal Ink** (economics). Everything is free and open source;
it runs on a laptop and, later, in GitHub Actions.

## The pipeline

A lesson is one YAML file (`channels/<name>/lessons/<CODE>.yaml`). Rendering it
is a chain of idempotent, content-hash-cached stages:

```
lesson.yaml
   │  lint      drawn_schema  — schema, {id} placeholders, word budget, LaTeX, licence
   ▼
   │  tts       drawn_tts     — Kokoro (→ edge-tts fallback) per-scene WAV +
   │                            faster-whisper word timings + each item's write-start
   ▼
   │  render    drawn_board   — Manim: formulas as MathTex, prose in Kalam, a hand
   │                            follows the pen; each item written on its word cue
   ▼
   │  assemble  packages/assemble (Remotion) — stitch clips + audio + captions,
   │                            title/end cards, and the thumbnail Still
   ▼
   │  finish    drawn_finish  — music bed, loudnorm to −14 LUFS, mux; writes
   │                            meta.md (CC BY attribution, tags, chapters) + captions.srt
   ▼
out/<channel>/<CODE>/video.mp4  thumbnail.png  meta.md  captions.srt   (gitignored)
```

Output is 1920×1080 @ 30 fps; preview is 480p15 for fast iteration.

## The lesson contract

Narration is plain prose. Board items each have an `id` and are referenced
inline as `{id}`. Before synthesis, `{id}` is replaced by the item's `say`
text; the write-start of each item is the timestamp of its first spoken word
after whisper alignment. The linter enforces: the word count (±15 % of
`target_minutes × 145`), a `say` on every formula, a one-to-one match between
placeholders and items, valid LaTeX, and a CC-BY-family licence.

```yaml
- id: s2
  kind: board          # title | board | derivation | graph | summary | end
  narration: "Angular momentum, {L}, points along the axle."
  board:
    - id: L
      latex: "\\vec{L} = I\\vec{\\omega}"
      say: "L equals I omega"
```

## Quick start

```bash
# one-time system packages (see below), then:
just setup                      # python media runtime + placeholder hand + node deps
just preview pen-and-pendulum ME-25   # full 480p15 render of the demo lesson
# → out/pen-and-pendulum/ME-25/video.mp4
```

Other recipes: `just lint|tts|render|assemble|finish`, `just build` (1080p30),
`just fetch` (rebuild backlogs from the research spreadsheets), `just new-lesson
<channel> <CODE>`, `just test`.

## Requirements

Toolchain: Python 3.12 (uv), Node 22 (pnpm), FFmpeg, TeX Live (XeLaTeX/latex),
espeak-ng, and `just`. System libraries for Manim (Cairo, Pango) and for the
Remotion headless browser are also needed — see `CLAUDE.md` and the setup notes.
Per-channel palette, board colour, font and voice live in
`channels/<name>/channel.yaml`; everything else is shared code under
`packages/`.

## Layout

```
packages/schema    Lesson schema + linter + backlog importer + scaffolder
packages/tts       SpeechService (Kokoro + edge-tts) + whisper alignment
packages/board     Manim scene library (handwriting board, hand-follow)
packages/assemble  Remotion assembly (clips, captions, cards, thumbnail)
packages/finish    ffmpeg finish, meta.md, captions.srt
packages/cache     content-hash caching helpers
channels/<name>    channel.yaml, backlog.yaml, research/, lessons/
assets/            vendored Kalam font (OFL), placeholder hand
```
