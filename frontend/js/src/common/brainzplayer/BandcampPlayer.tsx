import { get as _get, isString } from "lodash";
import type * as React from "react";
import { faBandcamp } from "@fortawesome/free-brands-svg-icons";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { dataSourcesInfo } from "../../settings/brainzplayer/BrainzPlayerSettings";
import SubsonicPlayer, { SubsonicPlayerProps } from "./SubsonicPlayer";

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
}
