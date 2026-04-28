import * as React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBarcode,
  faCircleNodes,
  faCompactDisc,
  faHomeAlt,
  faLink,
  faMicrophone,
  faMusic,
} from "@fortawesome/free-solid-svg-icons";
import {
  brandAmazon as faAmazon,
  brandApple as faApple,
  brandBandcamp as faBandcamp,
  faDeezer,
  brandDiscord as faDiscord,
  brandFacebook as faFacebook,
  brandInstagram as faInstagram,
  brandLastfm as faLastfm,
  faLinkedinIn,
  brandMastodon as faMastodon,
  brandNapster as faNapster,
  brandPinterest as faPinterest,
  brandSnapchat as faSnapchat,
  brandSoundcloud as faSoundcloud,
  brandSpotify as faSpotify,
  brandTiktok as faTiktok,
  brandTwitch as faTwitch,
  brandX as faTwitter,
  brandVimeo as faVimeo,
  brandYoutube as faYoutube,
} from "../common/icons/brandIcons";
import { dataSourcesInfo } from "../settings/brainzplayer/BrainzPlayerSettings";

export type SimilarArtist = {
  artist_mbid: string;
  comment: string;
  gender: string | null;
  name: string;
  reference_mbid: string;
  score: number;
  type: "Group" | "Person";
};

export type ReleaseGroup = {
  caa_id: number;
  caa_release_mbid: string;
  date: string | null;
  mbid: string;
  name: string;
  type: string;
  artists: Array<MBIDMappingArtist>;
};

export type PopularRecording = {
  artist_mbids: string[];
  artist_name: string;
  artists?: Array<MBIDMappingArtist>;
  caa_id?: number;
  caa_release_mbid?: string;
  position?: number;
  length: number;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
  total_listen_count: number;
  total_user_count: number;
};

export type ListeningStats = {
  total_listen_count?: number;
  total_user_count?: number;
  listeners: Array<{
    user_name: string;
    listen_count: number;
  }>;
};

export function getRelIconLink(relName: string, relValue: string) {
  let icon;
  let color;
  let isYoutube = false;
  switch (relName) {
    case "streaming":
    case "free streaming":
      if (/spotify\.com/.test(relValue)) {
        icon = faSpotify;
        color = dataSourcesInfo.spotify.color;
      } else if (/soundcloud\.com/.test(relValue)) {
        icon = faSoundcloud;
        color = dataSourcesInfo.soundcloud.color;
      } else if (/music\.apple\.com|itunes\.apple\.com/.test(relValue)) {
        icon = faApple;
        color = dataSourcesInfo.appleMusic.color;
      } else if (/bandcamp\.com/.test(relValue)) {
        icon = faBandcamp;
        color = "#629AA9";
      } else if (/last\.fm|lastfm\.com/.test(relValue)) {
        icon = faLastfm;
        color = "#D51007";
      } else if (/deezer\.com/.test(relValue)) {
        icon = faDeezer;
        color = "#FF0090";
      } else if (/music\.amazon|amazon\.com\/music/.test(relValue)) {
        icon = faAmazon;
        color = "#FF9900";
      } else if (/napster\.com/.test(relValue)) {
        icon = faNapster;
      } else if (/youtube\.com|youtu\.be/.test(relValue)) {
        icon = faYoutube;
        color = dataSourcesInfo.youtube.color;
        isYoutube = true;
      } else {
        icon = faMusic;
      }
      break;
    case "lyrics":
      icon = faMicrophone;
      break;
    case "wikidata":
      icon = faBarcode;
      break;
    case "youtube":
    case "youtube music":
      icon = faYoutube;
      color = dataSourcesInfo.youtube.color;
      isYoutube = true;
      break;
    case "soundcloud":
      icon = faSoundcloud;
      color = dataSourcesInfo.soundcloud.color;
      break;
    case "official homepage":
      icon = faHomeAlt;
      break;
    case "bandcamp":
      icon = faBandcamp;
      color = "#629AA9";
      break;
    case "last.fm":
      icon = faLastfm;
      color = "#D51007";
      break;
    case "apple music":
      icon = faApple;
      color = dataSourcesInfo.appleMusic.color;
      break;
    case "get the music":
    case "purchase for mail-order":
    case "purchase for download":
    case "download for free":
      icon = faCompactDisc;
      break;
    case "social network":
    case "online community":
      if (/instagram/.test(relValue)) {
        icon = faInstagram;
      } else if (/facebook/.test(relValue)) {
        icon = faFacebook;
      } else if (/twitter\.com/.test(relValue) || /(?:^|\.)x\.com/.test(relValue)) {
        icon = faTwitter;
        color = "#55ACEE";
      } else if (/soundcloud/.test(relValue)) {
        icon = faSoundcloud;
        color = dataSourcesInfo.soundcloud.color;
      } else if (/tiktok/.test(relValue)) {
        icon = faTiktok;
      } else if (/vimeo/.test(relValue)) {
        icon = faVimeo;
      } else if (/snapchat/.test(relValue)) {
        icon = faSnapchat;
      } else if (/linkedin/.test(relValue)) {
        icon = faLinkedinIn;
      } else if (/discord/.test(relValue)) {
        icon = faDiscord;
      } else if (/twitch/.test(relValue)) {
        icon = faTwitch;
        color = "#9147FF";
      } else if (/pinterest/.test(relValue)) {
        icon = faPinterest;
        color = "#E60023";
      } else if (/mastodon/.test(relValue)) {
        icon = faMastodon;
        color = "#6364FF";
      } else {
        icon = faCircleNodes;
      }
      break;
    default:
      icon = faLink;
      break;
  }
  let style = {};
  if (isYoutube) {
    // Youtube forces us to follow their branding guidelines to the letter,
    // so we need to force a minimum height of 20px for the icon path inside the svg
    // [poo emoji]
    style = { height: "26.7px", width: "auto" };
  }
  return (
    <a
      key={relValue}
      href={relValue}
      title={relName}
      className="btn btn-icon btn-link"
      target="_blank"
      rel="noopener noreferrer"
    >
      <FontAwesomeIcon
        icon={icon}
        fixedWidth={!isYoutube}
        color={color}
        style={style}
      />
    </a>
  );
}

export function noop() {}

export function popularRecordingToListen(recording: PopularRecording): Listen {
  return {
    listened_at: 0,
    track_metadata: {
      artist_name: recording.artist_name,
      track_name: recording.recording_name,
      release_name: recording.release_name,
      additional_info: {
        artist_mbids: recording.artist_mbids,
        recording_mbid: recording.recording_mbid,
        duration_ms: recording.length,
        release_mbid: recording.release_mbid,
        tracknumber: recording.position ?? null,
      },
      mbid_mapping: {
        caa_id: recording.caa_id,
        caa_release_mbid: recording.caa_release_mbid,
        recording_mbid: recording.recording_mbid,
        release_mbid: recording.release_mbid,
        artist_mbids: recording.artist_mbids,
        artists: recording.artists,
      },
    },
  };
}
