import React from "react";
import {AbsoluteFill, continueRender, delayRender, staticFile} from "remotion";
import type {LessonProps} from "./types";

// Load the vendored handwriting font for the thumbnail title.
const useHandwritingFont = (family: string, file: string) => {
  const [handle] = React.useState(() => delayRender("load-font"));
  React.useEffect(() => {
    const face = new FontFace(family, `url(${staticFile(file)})`);
    face
      .load()
      .then((loaded) => {
        (document.fonts as FontFaceSet).add(loaded);
        continueRender(handle);
      })
      .catch(() => continueRender(handle));
  }, [family, file, handle]);
};

export const Thumbnail: React.FC<LessonProps> = (props) => {
  const {channel, lesson} = props;
  useHandwritingFont(channel.font_family, channel.font_file);
  const onPaper = channel.board.style === "paper";
  return (
    <AbsoluteFill
      style={{
        backgroundColor: channel.board.background,
        justifyContent: "center",
        padding: 120,
      }}
    >
      <div
        style={{
          fontFamily: `${channel.font_family}, sans-serif`,
          color: channel.board.ink,
          fontSize: 110,
          lineHeight: 1.1,
          fontWeight: 700,
        }}
      >
        {lesson.title}
      </div>
      <div
        style={{
          marginTop: 48,
          height: 10,
          width: 360,
          backgroundColor: channel.board.accent,
          borderRadius: 6,
        }}
      />
      <div
        style={{
          marginTop: 36,
          fontFamily: `${channel.font_family}, sans-serif`,
          color: onPaper ? channel.board.ink : channel.palette[0],
          fontSize: 54,
          opacity: 0.85,
        }}
      >
        {channel.display_name}
      </div>
    </AbsoluteFill>
  );
};
