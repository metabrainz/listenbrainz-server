import React, {useState} from 'react';
import { ResponsiveNetwork, NodeProps, LinkProps, NodeTooltipProps, NetworkSvgProps } from '@nivo/network';
import { animated, to } from '@react-spring/web';
import { InputNode } from '@nivo/network';
import type { NodeType, LinkType, GraphDataType } from './Data';

interface GraphProps {
    data: GraphDataType;
    onArtistChange: (artist_mbid: string) => void;
    background: string;
}

const SimilarArtistsGraph = (props: GraphProps) => {
    const MAX_LINES = 2;
    const MAX_WORD_LENGTH = 10;
    
    const CustomNodeComponent = <NodeType extends InputNode>({
        node,
        animated: animatedProps,
        onClick,
        onMouseEnter,
        onMouseMove,
        onMouseLeave,
    }: NodeProps<NodeType>) => (
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
            // SVG text does not allow for easy multi line text
            // So, we split the text into words and render each word as a separate tspan element in a different line
            // We use ellipsis if word length exceeds MAX_WORD_LENGTH or if number of words(each in a separate line) exceed MAX_LINES
            node.id.split(" ").map((word, index) => (
                index < MAX_LINES ?
                <animated.tspan x={0} dy={index === 0 ? "0" : to([animatedProps.size], size => size / 6)}>
                    {word.length > MAX_WORD_LENGTH ? word.substring(0, MAX_WORD_LENGTH - 3) + "..." : word}
                </animated.tspan>
                :
                index == MAX_LINES && <animated.tspan x={0} dy={to([animatedProps.size], size => size / 6)}>
                    ...
                </animated.tspan>
            ))
            }
        </animated.text>
        </animated.g>
    )
    
    const CustomNodeTooltipComponent = ({ node }: NodeTooltipProps<NodeType>) => (
        <div
            style={{
                background: node.color,
                color: '#ffffff',
                padding: '9px 12px',
                borderRadius: '3px'
            }}
        >
            <strong>{node.id}</strong>
            <br />
            {node.data.score != Infinity && <>Score: {node.data.score}</>}
        </div>
    )

    const chartProperties: NetworkSvgProps<NodeType, LinkType> = {
        data: props.data,
        height: 900,
        width: 1000,
        repulsivity: 200,
        iterations: 120,
        centeringStrength: 0.1,
        nodeBorderWidth: 5,
        linkThickness: 2,
        nodeColor: node => node.color,
        linkColor: { from: 'source.color'},
        linkDistance: link => link.distance,
        nodeSize: node => node.size,
        activeNodeSize: node => node.size * 1.2,
        inactiveNodeSize: node => node.size / 1.2,
        isInteractive: true,
        onClick: node => props.onArtistChange(node.data.artist_mbid)
    }
    
    return (
        props.data ?
        <div style={{ height: '94vh', background: props.background }}>
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
export default SimilarArtistsGraph;
