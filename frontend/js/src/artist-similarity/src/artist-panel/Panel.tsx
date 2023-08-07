import React from "react";
import "./Panel.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { ArtistType } from "../Data";
import InfoLookup from "./InfoLookup";

interface PanelProps {
    artist: ArtistType;
}
const Panel = (props: PanelProps) => {
    var wikiData: string = "No Wikipedia data found.";
    /*(async () => {
        if(props.artist)
            wikiData = await InfoLookup(props.artist.artist_mbid);
    })();*/
    return(
        props.artist ?
        <div 
        className="artist-panel"
        >
            <div 
            className="artist-header"
            >
                <h2>{props.artist.name!}</h2>
                <p>{props.artist.type!}</p>
            </div>
            <div
            className="artist-info"
            >
                <div
                className="area"
                >
                    <strong>Born: </strong>
                    <br />
                    <strong>Area: </strong>
                </div>
                <div
                className="wiki"
                >
                    {wikiData}
                </div>
                <div
                className="mb-link"
                >
                <a
                id="mb-link-button"
                href={`https://musicbrainz.org/artist/${props.artist.artist_mbid}`}
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