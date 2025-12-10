import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHeadphones } from "@fortawesome/free-solid-svg-icons";
import { YearInMusicProps } from "../YearInMusic";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import ListenCard from "../../../common/listens/ListenCard";
import { getEntityLink } from "../../stats/utils";
import ImageShareButtons from "./ImageShareButtons";

type YIMChartsProps = {
  yearInMusicData: YearInMusicProps["yearInMusicData"];
  userName: string;
  year: number;
  customStyles?: string;
};
export default function YIMCharts({
  yearInMusicData,
  userName,
  year,
  customStyles,
}: YIMChartsProps) {
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  if (!yearInMusicData) {
    return null;
  }
  const isCurrentUser = userName === currentUser?.name;
  const youOrUsername = isCurrentUser ? "you" : `${userName}`;
  const encodedUsername = encodeURIComponent(userName);
  const linkToUserProfile = `https://listenbrainz.org/user/${encodedUsername}`;
  const linkToThisPage = `${linkToUserProfile}/year-in-music/${year}`;
  return (
    <div className="section">
      {/* <div className="header">
        Charts
        <div className="subheader">
          {youOrUsername} {isCurrentUser ? "have" : "has"} great taste
        </div>
      </div> */}
      <div className="flex flex-wrap" style={{ gap: "2em" }}>
        {yearInMusicData.top_recordings && (
          <div className="content-card" id="top-tracks">
            <div className="heading">
              <h3>Top songs of {year}</h3>
            </div>
            <div className="scrollable-area card-bg">
              {yearInMusicData.top_recordings.slice(0, 50).map((recording) => {
                const listenHere: Listen = {
                  listened_at: 0,
                  track_metadata: {
                    artist_name: recording.artist_name,
                    track_name: recording.track_name,
                    release_name: recording.release_name,
                    additional_info: {
                      recording_mbid: recording.recording_mbid,
                      release_mbid: recording.release_mbid,
                      artist_mbids: recording.artist_mbids,
                    },
                    mbid_mapping: {
                      recording_mbid: recording.recording_mbid ?? "",
                      release_mbid: recording.release_mbid ?? "",
                      artist_mbids: recording.artist_mbids ?? [],
                      artists: recording.artists,
                      caa_id: recording.caa_id,
                      caa_release_mbid: recording.caa_release_mbid,
                    },
                  },
                };
                return (
                  <ListenCard
                    compact
                    key={`top-recordings-${recording.track_name}-${recording.recording_mbid}`}
                    listen={listenHere}
                    showTimestamp={false}
                    showUsername={false}
                  />
                );
              })}
            </div>
            <div className="yim-share-button-container">
              <ImageShareButtons
                svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=tracks`}
                shareUrl={`${linkToThisPage}#top-tracks`}
                // shareText="Check out my"
                shareTitle={`My top tracks of ${year}`}
                fileName={`${userName}-top-tracks-${year}`}
                customStyles={customStyles}
              />
            </div>
          </div>
        )}
        {yearInMusicData.top_artists && (
          <div className="content-card" id="top-artists">
            <div className="heading">
              <h3>Top artists of {year}</h3>
            </div>
            <div className="scrollable-area card-bg">
              {yearInMusicData.top_artists.slice(0, 50).map((artist) => {
                const details = getEntityLink(
                  "artist",
                  artist.artist_name,
                  artist.artist_mbid
                );
                const thumbnail = (
                  <span className="badge bg-info">
                    <FontAwesomeIcon
                      style={{ marginRight: "4px" }}
                      icon={faHeadphones}
                    />{" "}
                    {artist.listen_count}
                  </span>
                );
                const listenHere = {
                  listened_at: 0,
                  track_metadata: {
                    track_name: "",
                    artist_name: artist.artist_name,
                    additional_info: {
                      artist_mbids: [artist.artist_mbid],
                    },
                  },
                };
                return (
                  <ListenCard
                    compact
                    key={`top-artists-${artist.artist_name}-${artist.artist_mbid}`}
                    listen={listenHere}
                    customThumbnail={thumbnail}
                    listenDetails={details}
                    showTimestamp={false}
                    showUsername={false}
                  />
                );
              })}
            </div>
            <div className="yim-share-button-container">
              <ImageShareButtons
                svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=artists`}
                shareUrl={`${linkToThisPage}#top-artists`}
                // shareText="Check out my"
                shareTitle={`My top artists of ${year}`}
                fileName={`${userName}-top-artists-${year}`}
                customStyles={customStyles}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
