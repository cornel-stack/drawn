import React from "react";
import {Composition} from "remotion";
import {calculateLessonMetadata, Lesson} from "./Lesson";
import {Thumbnail} from "./Thumbnail";
import type {LessonProps} from "./types";

const DEFAULT_PROPS: LessonProps = {
  lesson: {id: "DEMO", title: "Demo lesson title", channel: "pen-and-pendulum"},
  format: "landscape",
  channel: {
    display_name: "Pen & Pendulum",
    board: {style: "paper", background: "#f4ecd8", ink: "#1b2a4a", accent: "#c2462f"},
    palette: ["#1b2a4a", "#c2462f"],
    font_family: "Kalam",
    font_file: "assets/fonts/Kalam-Regular.ttf",
    intro_seconds: 2,
    outro_seconds: 3,
  },
  fps: 30,
  width: 1920,
  height: 1080,
  scenes: [],
};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Lesson"
      component={Lesson}
      calculateMetadata={calculateLessonMetadata}
      durationInFrames={150}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={DEFAULT_PROPS}
    />
    <Composition
      id="Thumbnail"
      component={Thumbnail}
      durationInFrames={1}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={DEFAULT_PROPS}
    />
  </>
);
