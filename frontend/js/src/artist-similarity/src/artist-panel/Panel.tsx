import React, { useEffect, useState } from "react";
import "./Panel.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { ArtistType } from "../Data";
import infoLookup from "./infoLookup";
import parse from 'html-react-parser';
interface PanelProps {
    artist: ArtistType;
}

type ArtistInfoType = {
    name: string;
    type: string;
    born: string;
    area: string;
    wikiData: string;
    mbLink: string;
}
const Panel = (props: PanelProps) => {
    const [artistInfo, setArtistInfo] = useState<ArtistInfoType | null>(null);
    useEffect(() => {
        const getArtistInfo = async () => {
            let artistApiInfo = await infoLookup(props.artist.artist_mbid);
            const MB_URL = `https://musicbrainz.org/artist/${props.artist.artist_mbid}`;
            let newArtistInfo: ArtistInfoType = {
                name: props.artist.name,
                type: props.artist.type ?? "Unknown",
                born: artistApiInfo[1],
                area: artistApiInfo[2],
                wikiData: artistApiInfo[0],
                mbLink: MB_URL
            };
            setArtistInfo(newArtistInfo);
        }
        getArtistInfo();
    }, [props.artist]);
    
    return(
        artistInfo ?
        <div 
        className="artist-panel"
        >
            <div 
            className="artist-header"
            >
                <h2>{artistInfo.name}</h2>
                <p>{artistInfo.type}</p>
            </div>
            <div
            className="artist-info"
            >
                <div
                className="area"
                >
                    <strong>Born: </strong>{artistInfo.born}
                    <br />
                    <strong>Area: </strong>{artistInfo.area}
                </div>
                <div
                className="wiki"
                >
                    {artistInfo.wikiData}
                </div>
                <div
                className="mb-link"
                >
                <a
                id="mb-link-button"
                href={artistInfo.mbLink}
                target="_blank"
                >
                    More
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                </a>
                </div>
            </div>
            <div
            className="artist-top-album"
            >
                <hr />
                Cover Art 
                <br />
                Album Name
            </div>
            <div
            className="artist-top-track"
            >
                <hr />
                Cover Art
                <br />
                Track Name
            </div>
        </div>
        :
        <>
        </>
    );
}

export default Panel;
export type { ArtistInfoType };