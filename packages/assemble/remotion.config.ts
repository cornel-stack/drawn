import {Config} from "@remotion/cli/config";

// The public dir is pointed at the repo root at render time via --public-dir,
// so staticFile() can reach both out/<channel>/<CODE>/... clips and the
// vendored font under assets/. Overridable on the CLI.
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
