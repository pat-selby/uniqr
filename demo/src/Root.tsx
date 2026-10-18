import React from "react";
import { Composition } from "remotion";
import { SQUARE, Square } from "./Square";
import { FPS, HEIGHT, WIDTH } from "./theme";
import { TOTAL, Video } from "./Video";

export const Root: React.FC = () => (
  <>
    <Composition id="UniQRDemo" component={Video} durationInFrames={TOTAL} fps={FPS} width={WIDTH} height={HEIGHT} />
    <Composition id="UniQRDemoSquare" component={Square} durationInFrames={TOTAL} fps={FPS} width={SQUARE} height={SQUARE} />
  </>
);
