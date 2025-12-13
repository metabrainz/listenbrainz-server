import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faQuestionCircle } from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";
import { get } from "lodash";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { JSPFTrackToListen } from "../../../playlists/utils";
import ListenCard from "../../../common/listens/ListenCard";
import { getListenCardKey } from "../../../utils/utils";
import ImageShareButtons from "./ImageShareButtons";
import { YearInMusicProps } from "../YearInMusic";

export default function TopLevelPlaylist(props: {
  topLevelPlaylist: JSPFPlaylist;
  coverArtKey: string;
  userName: string;
  year: number;
  customStyles?: string;
}): JSX.Element {
  const { topLevelPlaylist, coverArtKey, userName, year, customStyles } = props;
  const { APIService } = React.useContext(GlobalAppContext);
  const encodedUsername = encodeURIComponent(userName);
  return (
    <div className="content-card mb-3" id={`${coverArtKey}`}>
      <div className="center-p">
        <object
          className="img-fluid"
          data={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=${coverArtKey}&branding=False`}
        >
          Playlist image
        </object>
      </div>
      <h3>
        <a
          href={topLevelPlaylist.identifier}
          target="_blank"
          rel="noopener noreferrer"
        >
          {topLevelPlaylist.title}{" "}
        </a>
        <FontAwesomeIcon
          icon={faQuestionCircle}
          data-tip
          data-for={`playlist-${coverArtKey}-tooltip`}
          size="xs"
        />
        <Tooltip id={`playlist-${coverArtKey}-tooltip`}>
          {topLevelPlaylist.annotation}
        </Tooltip>
      </h3>
      <div className="card-bg">
        {topLevelPlaylist.track.slice(0, 5).map((playlistTrack) => {
          const listen = JSPFTrackToListen(playlistTrack);
          //   listens.push(listen);
          let thumbnail;
          if (playlistTrack.image) {
            thumbnail = (
              <div className="listen-thumbnail">
                <img
                  src={playlistTrack.image}
                  alt={`Cover Art for ${playlistTrack.title}`}
                />
              </div>
            );
          }
          return (
            <ListenCard
              key={getListenCardKey(listen)}
              className="playlist-item-card"
              listen={listen}
              customThumbnail={thumbnail}
              compact
              showTimestamp={false}
              showUsername={false}
            />
          );
        })}
        <hr />
        <a
          href={topLevelPlaylist.identifier}
          className="btn btn-info w-100"
          target="_blank"
          rel="noopener noreferrer"
        >
          See the full playlist…
        </a>
      </div>
      <div className="yim-share-button-container">
        <ImageShareButtons
          svgURL={`${APIService.APIBaseURI}/art/year-in-music/${year}/${encodedUsername}?image=${coverArtKey}`}
          shareUrl={`https://listenbrainz.org/user/${encodedUsername}/year-in-music/${year}#${coverArtKey}`}
          // shareText="Check out my"
          shareTitle={`My ${year} playlist on ListenBrainz`}
          fileName={`${userName}-${coverArtKey}-${year}`}
          customStyles={customStyles}
        />
      </div>
    </div>
  );
}
export function getPlaylistByName(
  yearInMusicData: YearInMusicProps["yearInMusicData"] | undefined,
  playlistName: string,
  description?: string
): JSPFPlaylist | undefined {
  try {
    const playlist = get(yearInMusicData, playlistName);
    if (!playlist) {
      return undefined;
    }
    // Append manual description used in this page (rather than parsing HTML, ellipsis issues, etc.)
    if (description) {
      playlist.annotation = description;
    }
    return playlist;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error(`"Error parsing ${playlistName}:`, error);
    return undefined;
  }
}
