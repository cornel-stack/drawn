import React from "react";
import {AbsoluteFill, continueRender, delayRender, staticFile} from "remotion";
import type {LessonProps} from "./types";

// Load the vendored handwriting font for the thumbnail.
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

// Split the hook around the keyword so the keyword can be highlighted.
const splitHook = (hook: string, keyword: string | null) => {
  if (!keyword) return [{text: hook, hot: false}];
  const i = hook.toLowerCase().indexOf(keyword.toLowerCase());
  if (i < 0) return [{text: hook, hot: false}];
  return [
    {text: hook.slice(0, i), hot: false},
    {text: hook.slice(i, i + keyword.length), hot: true},
    {text: hook.slice(i + keyword.length), hot: false},
  ].filter((p) => p.text.length > 0);
};

export const Thumbnail: React.FC<LessonProps> = (props) => {
  const {channel, lesson, width} = props;
  useHandwritingFont(channel.font_family, channel.font_file);

  const accent = channel.palette[0] ?? channel.board.accent;
  const accent2 = channel.palette[2] ?? accent;
  const thumb = lesson.thumbnail ?? {hook: lesson.title, keyword: null, kicker: null};
  const parts = splitHook(thumb.hook, thumb.keyword ?? null);
  const font = `${channel.font_family}, sans-serif`;
  // scale from a 1920-wide design so preview + final match
  const u = width / 1920;

  return (
    <AbsoluteFill style={{backgroundColor: channel.board.background, overflow: "hidden"}}>
      {/* energetic accent shapes */}
      <div
        style={{
          position: "absolute",
          right: -260 * u,
          top: -260 * u,
          width: 720 * u,
          height: 720 * u,
          borderRadius: "50%",
          background: accent,
          opacity: 0.18,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: -140 * u,
          bottom: -260 * u,
          width: 1000 * u,
          height: 420 * u,
          background: accent2,
          opacity: 0.14,
          transform: "rotate(-12deg)",
        }}
      />
      {/* oversized faint curiosity mark */}
      <div
        style={{
          position: "absolute",
          right: 40 * u,
          bottom: -80 * u,
          fontFamily: font,
          fontSize: 760 * u,
          color: accent,
          opacity: 0.1,
          fontWeight: 700,
          lineHeight: 1,
        }}
      >
        ?
      </div>

      <AbsoluteFill style={{padding: `${110 * u}px ${120 * u}px`, justifyContent: "center"}}>
        {thumb.kicker ? (
          <div
            style={{
              fontFamily: font,
              color: accent,
              fontSize: 56 * u,
              fontWeight: 700,
              letterSpacing: 6 * u,
              textTransform: "uppercase",
              marginBottom: 26 * u,
            }}
          >
            {thumb.kicker}
          </div>
        ) : null}

        <div
          style={{
            fontFamily: font,
            color: channel.board.ink,
            fontSize: 176 * u,
            lineHeight: 1.02,
            fontWeight: 700,
            textShadow: `0 ${6 * u}px ${24 * u}px rgba(0,0,0,0.55)`,
          }}
        >
          {parts.map((p, k) =>
            p.hot ? (
              <span
                key={k}
                style={{
                  color: channel.board.background,
                  background: accent,
                  padding: `0 ${14 * u}px`,
                  borderRadius: 10 * u,
                  boxDecorationBreak: "clone",
                  WebkitBoxDecorationBreak: "clone",
                }}
              >
                {p.text}
              </span>
            ) : (
              <span key={k}>{p.text}</span>
            )
          )}
        </div>

        <div
          style={{
            position: "absolute",
            left: 120 * u,
            bottom: 70 * u,
            display: "flex",
            alignItems: "center",
            gap: 20 * u,
          }}
        >
          <div style={{width: 60 * u, height: 12 * u, background: accent, borderRadius: 6 * u}} />
          <div
            style={{
              fontFamily: font,
              color: channel.board.ink,
              fontSize: 48 * u,
              fontWeight: 700,
              opacity: 0.9,
            }}
          >
            {channel.display_name}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
