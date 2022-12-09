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
import * as React from "react";
import ListenControl from "../listens/ListenControl";
import { getRecordingMBID } from "../utils/utils";
import SoundcloudPlayer from "./SoundcloudPlayer";
import SpotifyPlayer from "./SpotifyPlayer";
import YoutubePlayer from "./YoutubePlayer";

type MenuOptionsProps = {
  currentListen?: Listen | JSPFTrack;
};

function MenuOptions(props: MenuOptionsProps) {
  const [dropdownActionsOpen, setDropdownActionsOpen] = React.useState(false);
  const { currentListen } = props;
  let recordingMBID;
  let spotifyURL;
  let youtubeURL;
  let soundcloudURL;
  if (currentListen) {
    recordingMBID = getRecordingMBID(currentListen as Listen);
    spotifyURL = SpotifyPlayer.getURLFromListen(currentListen);
    youtubeURL = YoutubePlayer.getURLFromListen(currentListen);
    soundcloudURL = SoundcloudPlayer.getURLFromListen(currentListen);
  }

  const toggleDropupMenu = () => {
    setDropdownActionsOpen(!dropdownActionsOpen);
  };
  // Handle clicking outside dropdown
  const wrapperRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownActionsOpen &&
        wrapperRef.current &&
        !wrapperRef.current?.contains(event.target as Node)
      ) {
        setDropdownActionsOpen(false);
      }
    }
    // Bind
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      // dispose
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [wrapperRef, dropdownActionsOpen]);

  return (
    <div
      ref={wrapperRef}
      aria-label="Actions menu"
      aria-haspopup="menu"
      aria-expanded={dropdownActionsOpen}
      onClick={toggleDropupMenu}
      onKeyDown={toggleDropupMenu}
      role="button"
      tabIndex={0}
    >
      <FontAwesomeIcon
        icon={faEllipsisV}
        title="More actions"
        aria-hidden="true"
      />
      {currentListen && (
        <ul
          className={`dropup-content ${dropdownActionsOpen ? " open" : ""}`}
          aria-label="actions submenu"
          role="menu"
        >
          {recordingMBID && (
            <ListenControl
              icon={faExternalLinkAlt}
              text="Open in MusicBrainz"
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
              text="Open in Spotify"
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
              text="Open in YouTube"
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
              text="Open in Soundcloud"
              link={soundcloudURL}
              anchorTagAttributes={{
                target: "_blank",
                rel: "noopener noreferrer",
              }}
            />
          )}
        </ul>
      )}
    </div>
  );
}

export default MenuOptions;
