import React, { useContext, useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faGear,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import ReleaseCard from "../../fresh-releases/ReleaseCard";
import { ToastMsg } from "../../../notifications/Notifications";
import GlobalAppContext from "../../../utils/GlobalAppContext";

interface PanelProps {
  artist: ArtistType;
  onTrackChange: (currentTrack: Array<Listen>) => void;
}

type ArtistInfoType = {
  name?: string;
  type?: string;
  born: string;
  area: string;
  wiki: string;
  mbLink: string;
  topAlbum?: RecordingType | null;
  topTrack: RecordingType | null;
};

// Type for both top track and album i.e. a MB recording.
type RecordingType = {
  release_mbid: string;
  // Release name in case of an album
  release_name: string;
  // Recording name in case of a track
  recording_mbid?: string;
  recording_name?: string;
  caa_id: number;
  caa_release_mbid: string;
  artist_mbids: Array<string>;
  artist_name: string;
};

function Panel({ artist, onTrackChange }: PanelProps) {
  const [artistInfo, setArtistInfo] = useState<ArtistInfoType | null>(null);
  const { APIService } = useContext(GlobalAppContext);

  const [isSidebarOpen, setIsSidebarOpen] = React.useState<boolean>(false);
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const handleTrackChange = () => {
    if (artistInfo?.topTrack?.recording_name) {
      const newTrack: Array<Listen> = [
        {
          listened_at: 0,
          track_metadata: {
            artist_name: artist.name,
            track_name: artistInfo.topTrack.recording_name,
            release_name: artistInfo.topTrack.release_name,
            release_mbid: artistInfo.topTrack.release_mbid,
            recording_mbid: artistInfo.topTrack.recording_mbid,
          },
        },
      ];
      onTrackChange(newTrack);
    }
  };

  useEffect(() => {
    const fetchArtistInfo = async (
      artistMBID: string,
      artistData: ArtistType
    ) => {
      const artistInformation = await APIService.lookupMBArtist(artistMBID, "");
      const birthAreaData = {
        born: artistInformation?.["life-span"]?.begin || "Unknown",
        area: artistInformation?.area?.name || "Unknown",
      };

      const wikipediaData = await APIService.getArtistWikipediaExtract(
        artistMBID
      );

      const topRecordingsForArtist = await APIService.getTopRecordingsForArtist(
        artistMBID
      );

      return {
        name: artistData.name,
        type: artistData.type,
        ...birthAreaData,
        wiki: wikipediaData,
        mbLink: `https://musicbrainz.org/artist/${artistMBID}`,
        topTrack: topRecordingsForArtist?.[0] ?? null,
      };
    };

    const getArtistInfo = async () => {
      try {
        const artistFetchedInformation = await fetchArtistInfo(
          artist.artist_mbid,
          artist
        );
        setArtistInfo(artistFetchedInformation);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    };
    getArtistInfo();
  }, [APIService, artist]);

  return (
    artistInfo && (
      <>
        <div className={`sidebar ${isSidebarOpen ? "open" : ""}`}>
          <div className="sidebar-header">
            <p id="artist-name">{artistInfo.name}</p>
            <p id="artist-type">{artistInfo.type}</p>
          </div>
          <div className="artist-panel-info">
            <div className="artist-birth-area">
              <strong>Born: </strong>
              {artistInfo.born}
              <br />
              <strong>Area: </strong>
              {artistInfo.area}
            </div>
            <div id="artist-wiki">{artistInfo.wiki}</div>
            <div className="artist-mb-link">
              <a
                id="artist-mb-link-button"
                href={artistInfo.mbLink}
                target="_blank"
                rel="noreferrer"
              >
                <strong>More </strong>
                <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
              </a>
            </div>
          </div>
          {artistInfo.topTrack && (
            <div className="artist-top-album-container">
              <h5>Top Album</h5>
              {/**
               * Needs to be replaced with top album when endpoint is available.
               */}
              {artistInfo.topTrack && (
                <ReleaseCard
                  releaseMBID={artistInfo.topTrack.release_mbid}
                  // TODO: Replace with actual release date when endpoint is available.
                  releaseDate="2023-11-23"
                  releaseName={artistInfo.topTrack.release_name}
                  artistMBIDs={artistInfo.topTrack.artist_mbids}
                  artistCreditName={artistInfo.topTrack.artist_name}
                  releaseTypePrimary="Album"
                  releaseTypeSecondary={undefined}
                  caaID={artistInfo.topTrack.caa_id}
                  caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                  showReleaseTitle
                  showArtist={false}
                  showInformation={false}
                  showTags={false}
                  showListens={false}
                  releaseTags={[]}
                  listenCount={0}
                />
              )}
            </div>
          )}
          {artistInfo.topTrack && (
            <div className="artist-top-track-container">
              <h5>Top Track</h5>
              {artistInfo.topTrack && (
                <ReleaseCard
                  releaseMBID={artistInfo.topTrack.release_mbid}
                  // TODO: Replace with actual release date when endpoint is available.
                  releaseDate="2023-11-23"
                  releaseName={artistInfo.topTrack.recording_name ?? "Unknown"}
                  artistMBIDs={artistInfo.topTrack.artist_mbids}
                  artistCreditName={artistInfo.topTrack.artist_name}
                  releaseTypePrimary="Recording"
                  releaseTypeSecondary={undefined}
                  caaID={artistInfo.topTrack.caa_id}
                  caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                  showReleaseTitle
                  showArtist={false}
                  showInformation={false}
                  showTags={false}
                  showListens={false}
                  releaseTags={[]}
                  listenCount={0}
                />
              )}
            </div>
          )}
        </div>
        <button
          className={`toggle-sidebar-button ${isSidebarOpen ? "open" : ""}`}
          onClick={toggleSidebar}
          type="button"
        >
          <FontAwesomeIcon icon={isSidebarOpen ? faXmark : faGear} size="2x" />
        </button>
        {isSidebarOpen && (
          <button
            className="sidebar-overlay"
            onClick={toggleSidebar}
            type="button"
          >
            {}
          </button>
        )}
      </>
    )
  );
}

export default Panel;
