import * as React from "react";
import * as blobs2Animate from "blobs/v2/animate";

type BlobProps = {
  width: number;
  height: number;
  randomness: number;
  style?: React.CSSProperties;
} & Pick<HTMLCanvasElement, "className">;

export default function Blob({
  width,
  height,
  className,
  randomness,
  style,
}: BlobProps) {
  const blobCanvas = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const ctx = blobCanvas.current?.getContext("2d");
    if (!ctx) {
      return;
    }
    const animation = blobs2Animate.canvasPath();
    const randomAngleStart = Math.random() * 360;

    const renderAnimation: FrameRequestCallback = (time) => {
      ctx.clearRect(0, 0, width, height);
      let angle = (((time / 50) % 360) / 180) * Math.PI;
      angle += randomAngleStart;
      const gradient = ctx.createLinearGradient(
        width / 2,
        0,
        width / 2 + Math.cos(angle) * width,
        Math.sin(angle) * height
      );
      gradient.addColorStop(0, "#cd9a3b");
      gradient.addColorStop(1, "#5f5a97");
      ctx.fillStyle = gradient;
      ctx.fill(animation.renderFrame());
      requestAnimationFrame(renderAnimation);
    };
    requestAnimationFrame(renderAnimation);

    const size = Math.min(width, height);

    blobs2Animate.wigglePreset(
      animation,
      {
        seed: Date.now(),
        extraPoints: 3,
        randomness: randomness * 2,
        size,
      },
      { offsetX: 0, offsetY: 0 },
      { speed: Math.random() * 1.7 }
    );
  }, [blobCanvas, height, width, randomness]);

  return (
    <canvas
      width={width}
      height={height}
      className={className}
      ref={blobCanvas}
      style={style}
    />
  );
}
