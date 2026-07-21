import { get as _get, isString } from "lodash";
import type * as React from "react";
import { faBandcamp } from "@fortawesome/free-brands-svg-icons";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import SubsonicPlayer, {
  searchForSubsonicTrack,
  SubsonicPlayerProps,
} from "./SubsonicPlayer";
import { getTrackName } from "../../utils/utils";

export type BandcampPlayerProps = SubsonicPlayerProps;

export default class BandcampPlayer extends SubsonicPlayer {
  static contextType = GlobalAppContext;

  static hasPermissions = (bandcampUser?: BandcampUser) => {
    return Boolean(bandcampUser?.md5_auth_token && bandcampUser?.instance_url);
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      isString(musicService) && musicService.toLowerCase().includes("bandcamp")
    );
  }

  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: BandcampPlayerProps) {
    super(props, {
      name: "bandcamp",
      displayName: "Bandcamp",
      icon: faBandcamp,
      iconColor: dataSourcesInfo.bandcamp.color,
      className: "bandcamp-player",
      testId: "bandcamp-player",
      useProxy: true,
      proxyBaseUrl: "/settings/music-services/bandcamp",
    });
  }

  getSubsonicUser = (): BandcampUser | undefined => {
    const { bandcampAuth: bandcampUser = undefined } = this.context;
    return bandcampUser;
  };

  hasPermissions = (): boolean => {
    return BandcampPlayer.hasPermissions(this.getSubsonicUser());
  };

  searchAndPlayTrack = async (
    listen: Listen | JSPFTrack,
    signal: AbortSignal,
    searchController: AbortController
  ): Promise<void> => {
    const trackName = getTrackName(listen);
    const { handleError, handleWarning, onTrackNotFound } = this.props;

    if (!trackName) {
      handleWarning(
        "We are missing a track title to search on Bandcamp",
        "Not enough info to search on Bandcamp"
      );
      onTrackNotFound();
      return;
    }

    try {
      const track = await searchForSubsonicTrack(
        "",
        "",
        trackName,
        "",
        // bandcamp does not return MBIDs in the response, skip that matching behavior
        undefined,
        signal,
        this.getProxyUrl("search")
      );

      if (searchController !== this.abortController) {
        return;
      }

      if (track) {
        this.setState({ currentTrack: track });
        const audioElement = this.audioRef.current;
        if (audioElement) {
          const streamUrl = this.getSubsonicStreamUrl(track.id);
          this.setAudioSrc(audioElement, streamUrl);
          await audioElement.play();
          return;
        }
      }

      if (signal.aborted) {
        return;
      }

      onTrackNotFound();
    } catch (errorObject) {
      if (errorObject.name === "AbortError") {
        return;
      }

      if (errorObject.status === 401) {
        this.handleAuthenticationError();
        return;
      }

      handleError(
        errorObject.message ?? errorObject,
        "Error searching on Bandcamp"
      );
      onTrackNotFound();
    }
  };
}
