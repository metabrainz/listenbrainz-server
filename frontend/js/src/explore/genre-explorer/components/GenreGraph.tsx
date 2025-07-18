import * as React from "react";
import { ResponsiveNetwork } from "@nivo/network";
import { animated, to } from "@react-spring/web";
import tinycolor from "tinycolor2";

interface GenreNodeProps {
  id: string;
  name: string;
  size: number;
  color: string;
}

interface GenreLinkProps {
  source: string;
  target: string;
}

interface GraphDataType {
  nodes: GenreNodeProps[];
  links: GenreLinkProps[];
}

interface GraphProps {
  data: GraphDataType;
  onGenreChange: (genreMBID: string) => void;
  graphParentElementRef: React.RefObject<HTMLDivElement>;
}

function CustomNodeComponent({ node, animated: animatedProps, onClick }: any) {
  const genreName = node.data.name;
  const genreMBID = node.data.id;
  return (
    <animated.g
      className="genre-graph-node"
      transform={to(
        [animatedProps.x, animatedProps.y, animatedProps.scale],
        (x, y, scale) => `translate(${x},${y}) scale(${scale})`
      )}
      onClick={onClick ? (event) => onClick(node, event) : undefined}
      key={genreMBID}
    >
      <animated.circle
        r={to([animatedProps.size], (size) => size / 2)}
        fill={animatedProps.color}
        strokeWidth={1}
        stroke={tinycolor(node.color).darken(15).toString()}
        opacity={animatedProps.opacity}
      />
      <animated.foreignObject
        fontSize={to([animatedProps.size], (size) => size / 6)}
        width={to([animatedProps.size], (size) => size)}
        height={to([animatedProps.size], (size) => size)}
        x={to([animatedProps.size], (size) => -size / 2)}
        y={to([animatedProps.size], (size) => -size / 2)}
      >
        <div className="centered-text" title={genreName}>
          <div className="centered-text-inner">{genreName}</div>
        </div>
      </animated.foreignObject>
    </animated.g>
  );
}

function GenreGraph({
  data,
  onGenreChange,
  graphParentElementRef,
}: GraphProps) {
  const minimalSize = 650;
  const [width, setWidth] = React.useState(minimalSize);
  const [height, setHeight] = React.useState(minimalSize);

  React.useEffect(() => {
    if (!graphParentElementRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      setWidth(Math.max(minimalSize, entries[0].contentRect.width));
      setHeight(Math.max(minimalSize, entries[0].contentRect.height));
    });

    resizeObserver.observe(graphParentElementRef.current);
    // eslint-disable-next-line consistent-return
    return () => resizeObserver.disconnect();
  }, [graphParentElementRef]);

  return (
    <div
      className="genre-graph-container"
      ref={graphParentElementRef}
      style={{ height: "calc(100vh - 100px)" }}
    >
      <ResponsiveNetwork
        data={data}
        margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
        repulsivity={Math.min(width, height) / 2}
        centeringStrength={0.1}
        nodeBorderWidth={0}
        iterations={60}
        distanceMin={60}
        distanceMax={Math.min(width, height) / 2}
        nodeColor={(node) => node.color}
        linkThickness={1}
        nodeSize={(node) => node.size}
        activeNodeSize={(node) => node.size * 1.2}
        inactiveNodeSize={(node) => node.size}
        nodeComponent={CustomNodeComponent}
        onClick={(node) => onGenreChange(node.data.name)}
        motionConfig="default"
        animate
        isInteractive
      />
    </div>
  );
}

export default GenreGraph;
