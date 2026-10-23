export type Word = {word: string; start: number; end: number};

export type Scan = {
  id: string;
  kind: string;
  clip: string;
  audio: string;
  duration: number;
  words: Word[];
};

export type BoardStyle = {
  style: "paper" | "board";
  background: string;
  ink: string;
  accent: string;
};

export type Channel = {
  display_name: string;
  board: BoardStyle;
  palette: string[];
  font_family: string;
  font_file: string;
  intro_seconds: number;
  outro_seconds: number;
};

export type LessonProps = {
  lesson: {id: string; title: string; channel: string};
  format: "landscape" | "shorts";
  channel: Channel;
  fps: number;
  width: number;
  height: number;
  scenes: Scan[];
};
