import { get as _get, isString } from "lodash";
import type * as React from "react";
import { faNavidrome } from "../icons/faNavidrome";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import SubsonicPlayer, { SubsonicPlayerProps } from "./SubsonicPlayer";

export type NavidromePlayerProps = SubsonicPlayerProps;

export default class NavidromePlayer extends SubsonicPlayer {
  static contextType = GlobalAppContext;

  static hasPermissions = (navidromeUser?: NavidromeUser) => {
    return Boolean(
      navidromeUser?.md5_auth_token && navidromeUser?.instance_url
    );
  };

  static isListenFromThisService(listen: Listen | JSPFTrack): boolean {
    const musicService = _get(
      listen,
      "track_metadata.additional_info.music_service"
    );
    return (
      isString(musicService) && musicService.toLowerCase().includes("navidrome")
    );
  }

  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: NavidromePlayerProps) {
    super(props, {
      name: "navidrome",
      displayName: "Navidrome",
      icon: faNavidrome,
      iconColor: dataSourcesInfo.navidrome.color,
      className: "navidrome-player",
      testId: "navidrome-player",
      useProxy: false,
      proxyBaseUrl: "/settings/music-services/navidrome",
    });
  }

  getSubsonicUser = (): NavidromeUser | undefined => {
    const { navidromeAuth: navidromeUser = undefined } = this.context;
    return navidromeUser;
  };

  hasPermissions = (): boolean => {
    return NavidromePlayer.hasPermissions(this.getSubsonicUser());
  };

  getNavidromeInstanceURL = (): string => {
    return this.getSubsonicInstanceURL();
  };

  getNavidromeStreamUrl = (trackId: string): string => {
    return this.getSubsonicStreamUrl(trackId);
  };

  getTrackWebUrl = (track: NavidromeTrack): string => {
    try {
      const instanceURL = this.getNavidromeInstanceURL();

      // Link to the album page where the song appears instead
      if (track.albumId) {
        return `${instanceURL}/#/album/${track.albumId}/show`;
      }

      // Fallback to song list if no album ID is available
      return `${instanceURL}/#/song`;
    } catch (error) {
      // Fallback to empty string if we can't construct the URL
      return "";
    }
  };
}
