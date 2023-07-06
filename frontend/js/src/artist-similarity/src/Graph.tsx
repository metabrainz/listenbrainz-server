import React, {useState} from 'react';
import { ResponsiveNetwork, NodeProps, LinkProps, NodeTooltipProps, NetworkSvgProps } from '@nivo/network';
import { animated, to } from '@react-spring/web';
import { InputNode } from '@nivo/network';
interface GraphProps {
    data: any;
    fetchData: Function;
    backgroundColor: string;
}

const Graph = (props: GraphProps) => {
    type Node = (typeof props.data)['nodes'][number];
    type Link = (typeof props.data)['links'][number];
    const CustomNodeComponent = <Node extends InputNode>({
        node,
        animated: animatedProps,
        onClick,
        onMouseEnter,
        onMouseMove,
        onMouseLeave,
    }: NodeProps<Node>) => (
        <animated.g 
        transform={to([animatedProps.x, animatedProps.y, animatedProps.scale], (x, y, scale) => {
            return `translate(${x},${y}) scale(${scale})`
        })}
        onClick={onClick ? event => onClick(node, event) : undefined}
        onMouseEnter={onMouseEnter ? event => onMouseEnter(node, event) : undefined}
        onMouseMove={onMouseMove ? event => onMouseMove(node, event) : undefined}
        onMouseLeave={onMouseLeave ? event => onMouseLeave(node, event) : undefined}
        width={to([animatedProps.size], size => size / 2)}
        height={to([animatedProps.size], size => size / 2)}
        >
        <animated.circle
            data-testid={`node.${node.id}`}
            r={to([animatedProps.size], size => size / 2)}
            fill={animatedProps.color}
            strokeWidth={animatedProps.borderWidth}
            stroke={animatedProps.borderColor}
            opacity={animatedProps.opacity}
        />
        <animated.text 
        textAnchor="middle"
        dominantBaseline="alphabetic"
        fontSize={to([animatedProps.size], size => size / 6)}
        style={{ pointerEvents: 'none', fill: 'white'}}
        >
            {
            node.id.split(" ").map((word, index) => (
                index < 2 ?
                <animated.tspan x={0} dy={index === 0 ? "0" : to([animatedProps.size], size => size / 6)}>
                    {word.length > 10 ? word.substring(0, 10) + "..." : word}
                </animated.tspan>
                :
                index == 2 && <animated.tspan x={0} dy={to([animatedProps.size], size => size / 6)}>
                    ...
                </animated.tspan>
            ))
            }
        </animated.text>
        </animated.g>
    )
    
    const CustomNodeTooltipComponent = ({ node }: NodeTooltipProps<Node>) => (
        <div
            style={{
                background: node.color,
                color: '#ffffff',
                padding: '9px 12px',
                borderRadius: '3px'
            }}
        >
            <strong>Name: {node.id}</strong>
            <br />
            {node.data.score!= 0 && <>Score: {node.data.score}</>}
        </div>
    )

    const chartProperties: NetworkSvgProps<Node, Link> = {
        data: props.data,
        height: 1000,
        width: 1000,
        repulsivity: 200,
        iterations: 120,
        centeringStrength: 0.1,
        nodeBorderWidth: 5,
        linkThickness: 2,
        nodeColor: node => node.color,
        linkColor: { from: 'source.color', modifiers: [['brighter', 0.8]] },
        linkDistance: link => link.distance,
        nodeSize: node => node.size,
        activeNodeSize: node => node.size * 1.2,
        inactiveNodeSize: node => node.size / 1.2,
        isInteractive: true,
        onClick: node => props.fetchData(node.data.artist_mbid)
    }
    
    return (
        props.data ?
        <div style={{ height: '1000px', background: props.backgroundColor }}>
            <ResponsiveNetwork
                {...chartProperties}
                nodeComponent={CustomNodeComponent}
                nodeTooltip={CustomNodeTooltipComponent}
            />
        </div>
        :
        <p>
            Please wait...
        </p>
    );
}
export default Graph;
