import React, { useEffect, useState } from "react";
import "./Panel.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { ArtistType } from "../Data";
import infoLookup from "./infoLookup";
import ReleaseCard from "./ReleaseCard";
interface PanelProps {
    artist: ArtistType;
}

type ArtistInfoType = {
    name?: string;
    type?: string;
    born: string;
    area: string;
    wiki: string;
    mbLink: string;
    topAlbum?: RecordingType | null,
    topTrack: RecordingType | null
}

// Type for both top track and album i.e. a MB recording.
type RecordingType = {
    release_mbid: string;
    // Release name in case of an album
    release_name: string;
    // Recording name in case of a track
    recording_mbid?:string;
    recording_name?: string;
    caa_id: number;
    caa_release_mbid: string;
}
const Panel = (props: PanelProps) => {
    const [artistInfo, setArtistInfo] = useState<ArtistInfoType | null>(null);
    useEffect(() => {
        const getArtistInfo = async () => {
            let artistApiInfo = await infoLookup(props.artist.artist_mbid);
            const MB_URL = `https://musicbrainz.org/artist/${props.artist.artist_mbid}`;
            let newArtistInfo = artistApiInfo;
            // Adding name & type properties to artist info.
            newArtistInfo.name = props.artist.name;
            newArtistInfo.type = props.artist.type;
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
                    {artistInfo.wiki}
                </div>
                <div
                className="mb-link"
                >
                <a
                id="mb-link-button"
                href={artistInfo.mbLink}
                target="_blank"
                >
                    <strong>More </strong>
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                </a>
                </div>
            </div>
            { artistInfo.topTrack &&
                <div
                className="artist-top-album"
                >
                    <h3>Top Album</h3>
                    {/** 
                    * Needs to be replaced with top album when endpoint is available.
                    */}
                    { artistInfo.topTrack && 
                        <ReleaseCard 
                        releaseMBID={artistInfo.topTrack.release_mbid}
                        releaseName={artistInfo.topTrack.release_name}
                        caaID={artistInfo.topTrack.caa_id}
                        caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                        /> 
                    }
                </div>
            }
            { artistInfo.topTrack &&
                <div
                className="artist-top-track"
                >
                    <h3>Top Track</h3>
                    { artistInfo.topTrack && 
                        <ReleaseCard 
                        releaseMBID={artistInfo.topTrack.release_mbid}
                        releaseName={artistInfo.topTrack.recording_name ?? "Unknown"}
                        caaID={artistInfo.topTrack.caa_id}
                        caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                        recordingMBID={artistInfo.topTrack.recording_mbid}
                        /> 
                    }
                </div>
            }
        </div>
        :
        <>
        </>
    );
}

export default Panel;
export type { ArtistInfoType, RecordingType };