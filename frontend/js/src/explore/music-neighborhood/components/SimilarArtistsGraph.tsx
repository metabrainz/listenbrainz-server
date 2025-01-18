import * as React from "react";
import { ResponsiveNetwork, NodeProps, NetworkSvgProps } from "@nivo/network";
import { animated, to } from "@react-spring/web";
import { debounce, noop } from "lodash";
import tinycolor from "tinycolor2";

interface GraphProps {
  data: GraphDataType;
  onArtistChange: (artist_mbid: string) => void;
  background: string;
  graphParentElementRef: React.RefObject<HTMLDivElement>;
}

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
        filter="drop-shadow( 0px 4px 3px rgba(0, 0, 0, 0.2))"
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
        <div className="centered-text" title={node.data.artist_name}>
          <div className="centered-text-inner">{node.data.artist_name}</div>
        </div>
      </animated.foreignObject>
    </animated.g>
  );
}

function SimilarArtistsGraph({
  data,
  onArtistChange,
  background,
  graphParentElementRef,
}: GraphProps) {
  const minimalSize = 650;
  let initialWidth = minimalSize;
  let initialHeight = minimalSize;
  if (graphParentElementRef.current) {
    initialWidth = Math.max(
      minimalSize,
      graphParentElementRef.current.clientWidth
    );
    initialHeight = Math.max(
      minimalSize,
      graphParentElementRef.current.clientHeight
    );
  }
  const [width, setWidth] = React.useState(initialWidth);
  const [height, setHeight] = React.useState(initialHeight);

  React.useEffect(() => {
    if (!graphParentElementRef.current || !("ResizeObserver" in window))
      return noop;
    // Update the width and height on size change
    const observer = new ResizeObserver(
      debounce(
        (entries) => {
          setWidth(Math.max(minimalSize, entries[0].contentRect.width));
          setHeight(Math.max(minimalSize, entries[0].contentRect.height));
        },
        500,
        { leading: false }
      )
    );
    const originalRef = graphParentElementRef.current;
    observer.observe(originalRef);
    return () => originalRef && observer.unobserve(originalRef);
  }, [graphParentElementRef]);

  const chartProperties: NetworkSvgProps<NodeType, LinkType> = {
    data,
    repulsivity: Math.min(width, height) / 2,
    iterations: 40,
    centeringStrength: 0.1,
    nodeBorderWidth: 0,
    linkThickness: 1,
    distanceMin: 20,
    distanceMax: Math.min(width, height) / 2,
    width: width - 6,
    height: height - 6,
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
        // We can't set isInteractive to false (need onClick event)
        // But we don't want to show a tooltip, so this function returns an empty element
        // eslint-disable-next-line
        nodeTooltip={() => <></>}
      />
    </div>
  ) : (
    <p>Please wait...</p>
  );
}

export default SimilarArtistsGraph;
