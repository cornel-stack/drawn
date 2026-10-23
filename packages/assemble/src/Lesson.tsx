import React from "react";
import {
  AbsoluteFill,
  Audio,
  CalculateMetadataFunction,
  OffthreadVideo,
  Series,
  staticFile,
} from "remotion";
import {Captions} from "./Captions";
import type {LessonProps} from "./types";

const totalSeconds = (props: LessonProps) =>
  props.scenes.reduce((acc, s) => acc + s.duration, 0);

export const calculateLessonMetadata: CalculateMetadataFunction<LessonProps> = ({props}) => {
  const fps = props.fps;
  const shorts = props.format === "shorts";
  return {
    durationInFrames: Math.max(1, Math.ceil(totalSeconds(props) * fps)),
    fps,
    width: shorts ? 1080 : props.width,
    height: shorts ? 1920 : props.height,
  };
};

export const Lesson: React.FC<LessonProps> = (props) => {
  const {fps, scenes, channel} = props;
  return (
    <AbsoluteFill style={{backgroundColor: channel.board.background}}>
      <Series>
        {scenes.map((scene) => (
          <Series.Sequence
            key={scene.id}
            durationInFrames={Math.max(1, Math.round(scene.duration * fps))}
          >
            <AbsoluteFill>
              <OffthreadVideo src={staticFile(scene.clip)} />
              <Audio src={staticFile(scene.audio)} />
              <Captions words={scene.words} color={channel.board.accent} />
            </AbsoluteFill>
          </Series.Sequence>
        ))}
      </Series>
    </AbsoluteFill>
  );
};
