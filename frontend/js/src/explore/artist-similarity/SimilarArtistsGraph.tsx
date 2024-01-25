import * as React from "react";
import {
  ResponsiveNetwork,
  NodeProps,
  NodeTooltipProps,
  NetworkSvgProps,
} from "@nivo/network";
import { animated, to } from "@react-spring/web";
import { isFinite } from "lodash";
import tinycolor from "tinycolor2";

interface GraphProps {
  data: GraphDataType;
  onArtistChange: (artist_mbid: string) => void;
  background: string;
  graphParentElementRef: React.RefObject<HTMLDivElement>;
}

type OmitHeightWidth<T> = Omit<T, "height" | "width">;

function CustomNodeComponent({
  node,
  animated: animatedProps,
  onClick,
  onMouseEnter,
  onMouseMove,
  onMouseLeave,
}: NodeProps<NodeType>) {
  return (
    <animated.g
      className="artist-similarity-graph-node"
      transform={to(
        [animatedProps.x, animatedProps.y, animatedProps.scale],
        (x, y, scale) => {
          return `translate(${x},${y}) scale(${scale})`;
        }
      )}
      onClick={onClick ? (event) => onClick(node, event) : undefined}
      onMouseEnter={
        onMouseEnter ? (event) => onMouseEnter(node, event) : undefined
      }
      onMouseMove={
        onMouseMove ? (event) => onMouseMove(node, event) : undefined
      }
      onMouseLeave={
        onMouseLeave ? (event) => onMouseLeave(node, event) : undefined
      }
      width={to([animatedProps.size], (size) => size / 2)}
      height={to([animatedProps.size], (size) => size / 2)}
    >
      <animated.circle
        data-testid={`node.${node.id}`}
        r={to([animatedProps.size], (size) => size / 2)}
        fill={animatedProps.color}
        strokeWidth={animatedProps.borderWidth}
        stroke={animatedProps.borderColor}
        opacity={animatedProps.opacity}
      />
      <animated.foreignObject
        fontSize={to([animatedProps.size], (size) => size / 6)}
        color={tinycolor
          .mostReadable(node.color, ["#fff", "#46433a"])
          .toHexString()}
        width={to([animatedProps.size], (size) => size)}
        height={to([animatedProps.size], (size) => size)}
        x={to([animatedProps.size], (size) => -size / 2)}
        y={to([animatedProps.size], (size) => -size / 2)}
      >
        <div className="centered-text">
          <div className="centered-text-inner ellipsis-3-lines">
            {node.data.artist_name}
          </div>
        </div>
      </animated.foreignObject>
    </animated.g>
  );
}

function CustomNodeTooltipComponent({ node }: NodeTooltipProps<NodeType>) {
  return (
    <div
      style={{
        background: node.color,
        color: tinycolor
          .mostReadable(node.color, ["#fff", "#46433a"])
          .toHexString(),
        padding: "9px 12px",
        borderRadius: "3px",
      }}
    >
      <strong>{node.data.artist_name}</strong>
      <br />
      {isFinite(node.data.score) && <>Score: {node.data.score}</>}
    </div>
  );
}

function SimilarArtistsGraph({
  data,
  onArtistChange,
  background,
  graphParentElementRef,
}: GraphProps) {
  const chartProperties: OmitHeightWidth<NetworkSvgProps<
    NodeType,
    LinkType
  >> = {
    data,
    repulsivity: 180,
    iterations: 40,
    centeringStrength: 0.1,
    nodeBorderWidth: 0,
    linkThickness: 1,
    distanceMin: 20,
    distanceMax: graphParentElementRef?.current
      ? Math.min(
          550,
          graphParentElementRef.current.clientWidth / 2,
          graphParentElementRef.current.clientHeight / 2
        )
      : 550,
    nodeColor: (node) => node.color,
    linkColor: {
      from: "target.color",
      modifiers: [
        ["darker", 0.3],
        ["opacity", 0.7],
      ],
    },
    linkDistance: (link) => link.distance,
    nodeSize: (node) => node.size,
    activeNodeSize: (node) => node.size * 1.2,
    inactiveNodeSize: (node) => node.size,
    isInteractive: true,
    onClick: (node) => onArtistChange(node.data.artist_mbid),
    motionConfig: "default",
    margin: { top: 50 },
  };

  return data ? (
    <div
      className="artist-similarity-graph-container"
      id="artist-similarity-graph-container"
      style={{
        background,
      }}
      ref={graphParentElementRef}
    >
      <ResponsiveNetwork
        {...chartProperties}
        nodeComponent={CustomNodeComponent}
        nodeTooltip={CustomNodeTooltipComponent}
      />
    </div>
  ) : (
    <p>Please wait...</p>
  );
}

export default SimilarArtistsGraph;
