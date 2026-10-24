import React from "react";
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from "remotion";
import type {Word} from "./types";

const MAX_WORDS = 8;
const MAX_SECONDS = 3.5;

type Cue = {start: number; end: number; text: string};

const buildCues = (words: Word[]): Cue[] => {
  const cues: Cue[] = [];
  let bucket: Word[] = [];
  const flush = () => {
    if (bucket.length === 0) return;
    cues.push({
      start: bucket[0].start,
      end: bucket[bucket.length - 1].end,
      text: bucket.map((w) => w.word).join(" ").trim(),
    });
    bucket = [];
  };
  for (const w of words) {
    if (bucket.length >= MAX_WORDS || (bucket.length && w.end - bucket[0].start > MAX_SECONDS)) {
      flush();
    }
    bucket.push(w);
  }
  flush();
  return cues;
};

export const Captions: React.FC<{words: Word[]; color: string}> = ({words, color}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = frame / fps;
  const cues = buildCues(words);
  const active = cues.find((c) => t >= c.start && t <= c.end + 0.15);
  // A solid caption bar pinned to the bottom ~14% of the frame. The diagram
  // layer (Manim) keeps its content above this band, so they never collide.
  const barH = Math.round(height * 0.14);
  if (!active) {
    return (
      <AbsoluteFill style={{justifyContent: "flex-end"}}>
        <div style={{height: barH, background: "#0a0a0a", borderTop: "2px solid #222"}} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{justifyContent: "flex-end"}}>
      <div
        style={{
          height: barH,
          width: "100%",
          background: "#0a0a0a",
          borderTop: `3px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            maxWidth: width * 0.86,
            textAlign: "center",
            fontFamily: "sans-serif",
            fontSize: Math.round(width / 42),
            lineHeight: 1.25,
            color: "#ffffff",
          }}
        >
          {active.text}
        </div>
      </div>
    </AbsoluteFill>
  );
};
