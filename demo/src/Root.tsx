import React from "react";
import { Composition } from "remotion";
import { SQUARE, Square } from "./Square";
import { FPS, HEIGHT, WIDTH } from "./theme";
import { VERTICAL_FRAMES, VERTICAL_H, VERTICAL_W, Vertical } from "./Vertical";
import { Video, plan } from "./Video";

export const Root: React.FC = () => (
  <>
    {/* One cut per system; the landing page plays the visitor's. */}
    <Composition id="UniQRDemo" component={Video} defaultProps={{ platform: "windows" as const }} durationInFrames={plan("windows").total} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="UniQRDemoMac" component={Video} defaultProps={{ platform: "mac" as const }} durationInFrames={plan("mac").total} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="UniQRDemoLinux" component={Video} defaultProps={{ platform: "linux" as const }} durationInFrames={plan("linux").total} fps={FPS} width={WIDTH} height={HEIGHT} />
    {/* A vertical clip for phone feeds, about the scam check. */}
    <Composition id="UniQRScamCheckVertical" component={Vertical} durationInFrames={VERTICAL_FRAMES} fps={FPS} width={VERTICAL_W} height={VERTICAL_H} />
    <Composition id="UniQRDemoSquare" component={Square} durationInFrames={plan("windows").total} fps={FPS} width={SQUARE} height={SQUARE} />
  </>
);
