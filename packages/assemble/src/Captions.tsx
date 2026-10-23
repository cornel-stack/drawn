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
  const {fps, width} = useVideoConfig();
  const t = frame / fps;
  const cues = buildCues(words);
  const active = cues.find((c) => t >= c.start && t <= c.end + 0.15);
  if (!active) return null;
  return (
    <AbsoluteFill style={{justifyContent: "flex-end", alignItems: "center", padding: "0 0 48px"}}>
      <div
        style={{
          maxWidth: width * 0.8,
          textAlign: "center",
          fontFamily: "sans-serif",
          fontSize: Math.round(width / 34),
          lineHeight: 1.3,
          color: "#ffffff",
          background: "rgba(0,0,0,0.55)",
          padding: "10px 22px",
          borderRadius: 10,
          borderBottom: `4px solid ${color}`,
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
