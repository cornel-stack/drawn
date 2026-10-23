# drawn task runner. The same recipes run locally and in CI.
set shell := ["bash", "-cu"]

repo := justfile_directory()

# list recipes
default:
    @just --list

# install the full toolchain: python media runtime, placeholder hand, node deps
setup:
    uv sync --group media
    just hand
    cd {{repo}}/packages/assemble && pnpm install

# python deps only (schema/linter loop; no heavy render runtime)
setup-lite:
    uv sync

# (re)generate the placeholder hand PNG if assets/hand is empty
hand:
    uv run python -m drawn_board.make_placeholder_hand {{repo}}

# run all python tests
test:
    uv run pytest -q

# rebuild channels/*/backlog.yaml from the research spreadsheets
fetch:
    uv run python -m drawn_schema import-backlogs --repo-root {{repo}}

# scaffold a new lesson from its backlog row
new-lesson channel code:
    uv run python -m drawn_schema new-lesson {{channel}} {{code}} --repo-root {{repo}}

# lint a lesson (schema, placeholders, word budget, LaTeX, licence)
lint channel code:
    uv run python -m drawn_schema lint {{repo}}/channels/{{channel}}/lessons/{{code}}.yaml

# synthesise per-scene audio + word timestamps
tts channel code *FLAGS:
    uv run python -m drawn_tts {{repo}}/channels/{{channel}}/lessons/{{code}}.yaml --repo-root {{repo}} {{FLAGS}}

# render Manim scene clips (quality: preview|final)
render channel code quality="preview" *FLAGS:
    uv run python -m drawn_board {{repo}}/channels/{{channel}}/lessons/{{code}}.yaml --repo-root {{repo}} --quality {{quality}} {{FLAGS}}

# stitch clips + audio + captions with Remotion, plus the thumbnail Still
assemble channel code quality="preview":
    uv run python -m drawn_finish props {{repo}}/channels/{{channel}}/lessons/{{code}}.yaml --repo-root {{repo}} --quality {{quality}}
    cd {{repo}}/packages/assemble && pnpm exec remotion render src/index.ts Lesson {{repo}}/out/{{channel}}/{{code}}/assembly.mp4 --props={{repo}}/out/{{channel}}/{{code}}/props.json --public-dir={{repo}} --log=error
    cd {{repo}}/packages/assemble && pnpm exec remotion still src/index.ts Thumbnail {{repo}}/out/{{channel}}/{{code}}/thumbnail.png --props={{repo}}/out/{{channel}}/{{code}}/props.json --public-dir={{repo}} --log=error

# music bed + loudnorm + mux + meta.md + captions.srt
finish channel code:
    uv run python -m drawn_finish finish {{repo}}/channels/{{channel}}/lessons/{{code}}.yaml --repo-root {{repo}}

# full preview pipeline at 480p15 -> out/<channel>/<code>/video.mp4
preview channel code: (lint channel code) (tts channel code) (render channel code "preview") (assemble channel code "preview") (finish channel code)
    @echo "preview ready: out/{{channel}}/{{code}}/video.mp4"

# full build at 1080p30
build channel code: (lint channel code) (tts channel code) (render channel code "final") (assemble channel code "final") (finish channel code)
    @echo "build ready: out/{{channel}}/{{code}}/video.mp4"
