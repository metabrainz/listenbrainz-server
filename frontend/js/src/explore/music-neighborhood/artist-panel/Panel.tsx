import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowUpRightFromSquare,
  faInfo,
} from "@fortawesome/free-solid-svg-icons";
import Spinner from "react-loader-spinner";
import ReleaseCard from "../../fresh-releases/components/ReleaseCard";
import SideBar from "../../../components/Sidebar";

interface PanelProps {
  artistInfo: ArtistInfoType;
  loading: boolean;
}

function Panel({ artistInfo, loading }: PanelProps) {
  const { topTracks } = artistInfo;
  const topTrack = topTracks?.[0];

  return (
    artistInfo && (
      <SideBar toggleIcon={faInfo}>
        {loading ? (
          <div className="spinner-container">
            <Spinner
              type="ThreeDots"
              color="#eb743b"
              height={100}
              width={100}
              visible
            />
            <div
              className="text-muted"
              style={{ fontSize: "2rem", margin: "1rem" }}
            >
              Loading&#8230;
            </div>
          </div>
        ) : (
          <>
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
            {artistInfo.topAlbum && (
              <div className="artist-top-album-container">
                <h5>Top Album</h5>
                {artistInfo.topAlbum && (
                  <ReleaseCard
                    releaseMBID={artistInfo.topAlbum.release.caa_release_mbid}
                    releaseName={artistInfo.topAlbum.release.name}
                    artistMBIDs={artistInfo.topAlbum.artist.artists.map(
                      (topAlbumArtist) => topAlbumArtist.artist_mbid
                    )}
                    artistCreditName={artistInfo.topAlbum.artist.artist_credit_id.toString()}
                    caaID={artistInfo.topAlbum.release.caa_id}
                    caaReleaseMBID={
                      artistInfo.topAlbum.release.caa_release_mbid
                    }
                    showReleaseTitle
                    showTags
                    showListens
                    releaseTags={artistInfo.topAlbum.tag.release_group?.map(
                      (tag) => tag.tag
                    )}
                    listenCount={artistInfo.topAlbum?.total_listen_count}
                  />
                )}
              </div>
            )}
            {topTrack && (
              <div className="artist-top-track-container">
                <h5>Top Track</h5>
                {topTrack && (
                  <ReleaseCard
                    releaseMBID={topTrack.release_mbid}
                    releaseName={topTrack.recording_name ?? "Unknown"}
                    artistMBIDs={topTrack.artist_mbids}
                    artistCreditName={topTrack.artist_name}
                    caaID={topTrack.caa_id}
                    caaReleaseMBID={topTrack.caa_release_mbid}
                    showReleaseTitle
                    showListens
                    listenCount={topTrack.total_listen_count}
                  />
                )}
              </div>
            )}
          </>
        )}
      </SideBar>
    )
  );
}

export default Panel;
