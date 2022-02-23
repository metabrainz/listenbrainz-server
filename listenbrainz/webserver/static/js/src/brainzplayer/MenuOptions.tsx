import {
  faSoundcloud,
  faSpotify,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import {
  faEllipsisV,
  faExternalLinkAlt,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";
import ListenControl from "../listens/ListenControl";
import { getRecordingMBID } from "../utils/utils";
import SoundcloudPlayer from "./SoundcloudPlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";

type MenuOptionsProps = {
  currentListen?: Listen | JSPFTrack;
};

const MenuOptions = (props: MenuOptionsProps) => {
  const { currentListen } = props;
  if (!currentListen) {
    return (
      <FontAwesomeIcon
        icon={faEllipsisV}
        title="Actions"
        id="listenControlsDropdown"
        aria-haspopup="false"
        className="disabled"
      />
    );
  }

  const recordingMBID = getRecordingMBID(currentListen as Listen);
  const spotifyURL = SpotifyPlayer.getSpotifyURLFromListen(currentListen);
  const youtubeURL = YoutubePlayer.getYoutubeURLFromListen(currentListen);
  const soundcloudURL = SoundcloudPlayer.getSoundcloudURLFromListen(
    currentListen
  );

  return (
    <>
      <FontAwesomeIcon
        icon={faEllipsisV}
        title="Actions"
        className="dropdown-toggle"
        id="listenControlsDropdown"
        data-toggle="dropdown"
        aria-haspopup="true"
        aria-expanded="true"
      />
      <ul
        className="dropdown-menu dropdown-menu-right"
        aria-labelledby="listenControlsDropdown"
      >
        {recordingMBID && (
          <ListenControl
            icon={faExternalLinkAlt}
            title="Open in MusicBrainz"
            link={`https://musicbrainz.org/recording/${recordingMBID}`}
            anchorTagAttributes={{
              target: "_blank",
              rel: "noopener noreferrer",
            }}
          />
        )}
        {spotifyURL && (
          <ListenControl
            icon={faSpotify}
            title="Open in Spotify"
            link={spotifyURL}
            anchorTagAttributes={{
              target: "_blank",
              rel: "noopener noreferrer",
            }}
          />
        )}
        {youtubeURL && (
          <ListenControl
            icon={faYoutube}
            title="Open in YouTube"
            link={youtubeURL}
            anchorTagAttributes={{
              target: "_blank",
              rel: "noopener noreferrer",
            }}
          />
        )}
        {soundcloudURL && (
          <ListenControl
            icon={faSoundcloud}
            title="Open in Soundcloud"
            link={soundcloudURL}
            anchorTagAttributes={{
              target: "_blank",
              rel: "noopener noreferrer",
            }}
          />
        )}
      </ul>
    </>
  );
};

export default MenuOptions;
