/*
Shamelessly stolen from https://github.com/talor-hammond/react-colour-wheel
which is now unmaintained and fails to compile
*/

import * as React from "react";
import {
  colourToRgbObj,
  getEffectiveRadius,
  calculateBounds,
  produceRgbShades,
  convertObjToString,
} from "../utils/utils";
import defaultColors from "../utils/defaultColors";

type ColorWheelProps = {
  radius: number;
  lineWidth: number;
  onColorSelected: (rgbValue: string) => void;
  padding?: number;
  spacers?: {
    colour: string;
    shadowColor: string;
    shadowBlur: number | string;
  };
  colours?: string[];
  shades?: number;
  dynamicCursor?: boolean;
  preset?: boolean;
  presetColor?: string;
  animated?: boolean;
  onRef?: (arg?: ColorWheel) => void;
};
type ColorWheelState = {
  rgb: { r: string | number; g: string | number; b: string | number } | null;
  innerWheelOpen: boolean;
  centerCircleOpen: boolean;
};

const defaultProps = {
  colours: defaultColors,
  shades: 16,
  padding: 0,
  dynamicCursor: true,
  preset: false,
  animated: true,
  presetColor: "",
};

// Global-vars:
const fullCircle = 2 * Math.PI;
const quarterCircle = fullCircle / 4;

export default class ColorWheel extends React.Component<
  ColorWheelProps,
  ColorWheelState
> {
  outerWheelBounds: any = null;
  innerWheelBounds: any = null;
  centerCircleBounds: any = null;

  outerWheelRadius: any = null;
  innerWheelRadius: any = null;
  centerCircleRadius: any = null;
  firstSpacerRadius: any = null;
  secondSpacerRadius: any = null;

  canvasEl: React.RefObject<HTMLCanvasElement>;
  ctx: any = null;

  constructor(props: ColorWheelProps) {
    super(props);

    this.state = {
      rgb: null,
      innerWheelOpen: false,
      centerCircleOpen: false,
    };

    // Bindings:
    this.onCanvasHover = this.onCanvasHover.bind(this);
    this.onCanvasClick = this.onCanvasClick.bind(this);

    this.canvasEl = React.createRef<HTMLCanvasElement>();
  }

  // MARK - Life-cycle methods:
  UNSAFE_componentWillMount() {
    const { radius, lineWidth, padding } = this.props;

    // Setting effective radii:
    this.outerWheelRadius = radius;
    this.innerWheelRadius =
      this.outerWheelRadius - lineWidth - (padding ?? defaultProps.padding);
    this.centerCircleRadius =
      this.innerWheelRadius - lineWidth - (padding ?? defaultProps.padding);
    this.firstSpacerRadius = this.outerWheelRadius - lineWidth; // NOTE: effectiveRadius will take into account padding as lineWidth.
    this.secondSpacerRadius = this.innerWheelRadius - lineWidth;

    // Defining our bounds-objects, exposes a .inside(e) -> boolean method:
    this.outerWheelBounds = calculateBounds(radius - lineWidth, radius);
    this.innerWheelBounds = calculateBounds(
      this.innerWheelRadius - lineWidth,
      this.innerWheelRadius
    );
    this.centerCircleBounds = calculateBounds(0, this.centerCircleRadius);
    // this.firstSpacerBounds = calculateBounds(
    //   this.firstSpacerRadius - padding,
    //   this.firstSpacerRadius
    // );
    // this.secondSpacerBounds = calculateBounds(
    //   this.secondSpacerRadius - padding,
    //   this.secondSpacerRadius
    // );
  }

  componentDidMount() {
    const { onRef, preset, presetColor } = this.props;
    // Giving this context to our parent component.
    if (onRef) onRef(this);

    this.ctx = this.canvasEl.current?.getContext("2d");

    if (preset) {
      const rgb = colourToRgbObj(presetColor ?? defaultProps.presetColor);

      this.setState({ rgb }, () => {
        this.drawOuterWheel();
        this.drawInnerWheel();
        this.drawCenterCircle();
        this.drawSpacers();
      });
    } else {
      this.drawOuterWheel();
      this.drawSpacers();
    }
  }

  componentWillUnmount() {
    const { onRef, preset, presetColor } = this.props;
    if (onRef) {
      onRef(undefined);
    }
  }

  // MARK - mouse-events:
  onCanvasHover: React.MouseEventHandler<HTMLCanvasElement> = ({
    clientX,
    clientY,
  }) => {
    const { innerWheelOpen, centerCircleOpen } = this.state;
    const evt = this.getRelativeMousePos(clientX, clientY);
    const { current: canvasElement } = this.canvasEl;
    if (!canvasElement || !evt) {
      return;
    }
    // Cases for mouse-location:
    if (this.outerWheelBounds.inside(evt.fromCenter)) {
      canvasElement.style.cursor = "crosshair";
    } else if (this.innerWheelBounds.inside(evt.fromCenter) && innerWheelOpen) {
      canvasElement.style.cursor = "crosshair";
    } else if (
      this.centerCircleBounds.inside(evt.fromCenter) &&
      centerCircleOpen
    ) {
      // TODO: Have it clear on click?
      canvasElement.style.cursor = "pointer";
    } else {
      canvasElement.style.cursor = "auto";
    }
  };

  onCanvasClick: React.MouseEventHandler<HTMLCanvasElement> = ({
    clientX,
    clientY,
  }) => {
    const evt = this.getRelativeMousePos(clientX, clientY);
    if (!evt) {
      return;
    }
    const { innerWheelOpen } = this.state;
    // Cases for click-events:
    if (this.outerWheelBounds.inside(evt.fromCenter)) {
      this.outerWheelClicked(evt.onCanvas);
    } else if (this.innerWheelBounds.inside(evt.fromCenter) && innerWheelOpen) {
      this.innerWheelClicked(evt.onCanvas);
    }
  };

  // MARK - Common:
  getRelativeMousePos(
    clientX: number,
    clientY: number
  ): { fromCenter: number; onCanvas: { x: number; y: number } } | null {
    const { radius } = this.props;

    const canvasPos = this.canvasEl.current?.getBoundingClientRect();
    if (!canvasPos) {
      return null;
    }
    const h = radius * 2;
    const w = radius * 2;

    // evtPos relative to our canvas.
    const onCanvas = {
      x: clientX - canvasPos.left,
      y: clientY - canvasPos.top,
    };

    // e is our mouse-position relative to the center of the canvasEl; using pythag
    const fromCenter = Math.sqrt(
      (onCanvas.x - w / 2) * (onCanvas.x - w / 2) +
        (onCanvas.y - h / 2) * (onCanvas.y - h / 2)
    );

    // This returns an object in which we have both mouse-pos relative to the canvas, as well as the true-middle.
    return {
      fromCenter,
      onCanvas,
    };
  }

  initCanvas() {
    const { radius } = this.props;

    const width = radius * 2;
    const height = radius * 2;

    this.ctx.clearRect(0, 0, width, height);

    this.drawOuterWheel();
    this.drawSpacers();
  }

  // MARK - Clicks & action methods:
  outerWheelClicked(evtPos: { x: number; y: number }) {
    const { onColorSelected } = this.props;
    // returns an rgba array of the pixel-clicked.
    const rgbaArr = this.ctx.getImageData(evtPos.x, evtPos.y, 1, 1).data;
    const [r, g, b] = rgbaArr;

    const rgb = { r, g, b };

    // Whether the user wants rgb-strings or rgb objects returned.
    const rgbArg = convertObjToString(rgb); // TODO: Let user set different return values in props; e.g. rbg obj, string, etc.

    onColorSelected(rgbArg);

    this.setState(
      {
        rgb,
        innerWheelOpen: true,
        centerCircleOpen: true,
      },
      () => {
        this.drawInnerWheel();
        this.drawCenterCircle();
      }
    );
  }

  innerWheelClicked(evtPos: { x: number; y: number }) {
    const { onColorSelected } = this.props;
    const rgbaArr = this.ctx.getImageData(evtPos.x, evtPos.y, 1, 1).data;
    const [r, g, b] = rgbaArr;

    const rgb = { r, g, b };

    const rgbArg = convertObjToString(rgb);

    onColorSelected(rgbArg);

    this.setState(
      {
        rgb,
        centerCircleOpen: true,
      },
      () => {
        this.drawCenterCircle();
      }
    );
  }

  clear(callback?: () => void) {
    this.setState(
      {
        rgb: null,
        innerWheelOpen: false,
        centerCircleOpen: false,
      },
      () => {
        // Reset state & re-draw.
        this.initCanvas();
        if (callback) callback();
      }
    );
  }

  // MARK - Drawing:
  drawOuterWheel() {
    // TODO: Draw outline; separate method.
    const { radius, colours, lineWidth } = this.props;
    const height = radius * 2;
    const width = radius * 2;

    // This value ensures that the stroke accounts for the lineWidth provided to produce an accurately represented radius.
    const effectiveRadius = getEffectiveRadius(radius, lineWidth);

    // Converting each colour into a relative rgb-object we can iterate through.
    const rgbArr = (colours ?? defaultProps.colours).map((colour) =>
      colourToRgbObj(colour)
    );

    rgbArr.forEach((rgb, i) => {
      this.ctx.beginPath();

      // Creates strokes 1 / rgbArr.length of the circle circumference.
      const startAngle = (fullCircle / rgbArr.length) * i;
      const endAngle = (fullCircle / rgbArr.length) * (i + 1);

      this.ctx.arc(
        width / 2,
        height / 2,
        effectiveRadius,
        startAngle,
        endAngle
      );
      this.ctx.lineWidth = lineWidth; // This is the width of the innerWheel.

      // Stroke-style changes based on the shade:
      this.ctx.strokeStyle = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
      this.ctx.stroke();
      this.ctx.closePath();
    });
  }

  drawSpacers() {
    const { spacers } = this.props;
    if (spacers) {
      this.drawSpacer(this.firstSpacerRadius);
      this.drawSpacer(this.secondSpacerRadius);
    }
  }

  drawSpacer(spacerRadius: number) {
    const { radius, padding, spacers } = this.props;
    if (!spacers) {
      return;
    }
    const { colour, shadowColor, shadowBlur } = spacers;

    const height = radius * 2;
    const width = radius * 2;

    const effectiveRadius = getEffectiveRadius(
      spacerRadius,
      padding ?? defaultProps.padding
    );

    this.ctx.beginPath();

    this.ctx.arc(width / 2, height / 2, effectiveRadius, 0, fullCircle);
    this.ctx.lineWidth = padding;

    this.ctx.shadowColor = shadowColor;
    this.ctx.shadowBlur = shadowBlur;
    this.ctx.strokeStyle = colour;
    this.ctx.stroke();
    this.ctx.closePath();

    // To reset our shadowColor for other strokes.
    this.ctx.shadowColor = "transparent";
  }

  drawInnerWheel(startAnimationPercentage = 0) {
    let animationPercentage = startAnimationPercentage;
    // raf setup.
    // @ts-ignore
    const requestAnimationFrame =
      window.requestAnimationFrame ||
      // @ts-ignore
      window.mozRequestAnimationFrame ||
      // @ts-ignore
      window.webkitRequestAnimationFrame ||
      // @ts-ignore
      window.msRequestAnimationFrame;
    window.requestAnimationFrame = requestAnimationFrame;

    const { rgb } = this.state;
    const { radius, lineWidth, shades, animated } = this.props;

    const height = radius * 2;
    const width = radius * 2;

    const effectiveRadius = getEffectiveRadius(
      this.innerWheelRadius,
      lineWidth
    );

    // Re-initialising canvas.
    this.ctx.clearRect(0, 0, width, height);

    this.drawOuterWheel();
    this.drawSpacers();
    let rgbShades: any[] = [];
    if (rgb) {
      rgbShades = produceRgbShades(
        rgb.r,
        rgb.g,
        rgb.b,
        shades ?? defaultProps.shades
      );
    }

    // Different functions for drawing our inner-wheel of shades.
    const drawShades = () => {
      rgbShades.forEach((rgbShade, i) => {
        this.ctx.beginPath();

        const startAngle = (fullCircle / rgbShades.length) * i + quarterCircle;
        const endAngle =
          (fullCircle / rgbShades.length) * (i + 1) + (1 / 2) * Math.PI;

        this.ctx.arc(
          width / 2,
          height / 2,
          effectiveRadius,
          startAngle,
          endAngle
        );
        this.ctx.lineWidth = lineWidth; // This is the width of the innerWheel.

        // Stroke style changes based on the shade:
        this.ctx.strokeStyle = `rgb(${rgbShade.r}, ${rgbShade.g}, ${rgbShade.b})`;
        this.ctx.stroke();
        this.ctx.closePath();
      });
    };

    const animateShades = () => {
      rgbShades.forEach((rgbShade, i) => {
        this.ctx.beginPath();

        const startAngle = (fullCircle / rgbShades.length) * i + quarterCircle;
        const endAngle =
          (fullCircle / rgbShades.length) * (i + 1) + (1 / 2) * Math.PI;

        this.ctx.arc(
          width / 2,
          height / 2,
          effectiveRadius,
          startAngle,
          endAngle
        );
        this.ctx.lineWidth = lineWidth * animationPercentage; // This is the width of the innerWheel.

        // Stroke style changes based on the shade:
        this.ctx.strokeStyle = `rgb(${rgbShade.r}, ${rgbShade.g}, ${rgbShade.b})`;
        this.ctx.stroke();
        this.ctx.closePath();
      });

      // TODO: Make this animation speed dynamic.
      animationPercentage += 1 / 10; // i.e. 1 / x frames

      // Essentially re-draws rgbShades.forEach until the animationPercentage reaches 1, i.e. 100%
      if (animationPercentage < 1) requestAnimationFrame(animateShades);
    };

    if (animated) {
      animateShades();
    } else {
      // TODO: Refactor into its own func.
      drawShades();
    }
  }

  drawCenterCircle() {
    const { rgb } = this.state;
    const { radius } = this.props;

    const height = radius * 2;
    const width = radius * 2;
    this.ctx.lineWidth = 0;

    this.ctx.beginPath();
    this.ctx.arc(
      width / 2,
      height / 2,
      this.centerCircleRadius,
      0,
      2 * Math.PI
    );
    if (!rgb) {
      return;
    }
    this.ctx.fillStyle = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
    this.ctx.fill();
    this.ctx.lineWidth = 0.1;
    this.ctx.strokeStyle = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
    this.ctx.stroke();
    this.ctx.closePath();
  }

  render() {
    const { radius, dynamicCursor } = this.props;

    return dynamicCursor ? (
      <canvas
        data-testid="colour-picker"
        id="colour-picker"
        ref={this.canvasEl}
        onClick={this.onCanvasClick}
        onMouseMove={this.onCanvasHover}
        width={`${radius * 2}px`}
        height={`${radius * 2}px`}
      />
    ) : (
      <canvas
        id="colour-picker"
        data-testid="colour-picker"
        ref={this.canvasEl}
        onClick={this.onCanvasClick}
        width={`${radius * 2}px`}
        height={`${radius * 2}px`}
      />
    );
  }
}
