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
  faApple,
  faBandcamp,
  faFacebook,
  faInstagram,
  faLastfm,
  faSoundcloud,
  faTwitter,
  faYoutube,
} from "@fortawesome/free-brands-svg-icons";
import { compact } from "lodash";

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
  release_group_mbid: string;
  release_group_name: string;
  type: string;
};
export type PopularRecording = {
  artist_mbids: string[];
  artist_name: string;
  caa_id: number;
  caa_release_mbid: string;
  length: number;
  recording_mbid: string;
  recording_name: string;
  release_mbid: string;
  release_name: string;
  total_listen_count: number;
  total_user_count: number;
};

export function getRelIconLink(relName: string, relValue: string) {
  let icon;
  switch (relName) {
    case "streaming":
    case "free streaming":
      icon = faMusic;
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
      break;
    case "soundcloud":
      icon = faSoundcloud;
      break;
    case "official homepage":
      icon = faHomeAlt;
      break;
    case "bandcamp":
      icon = faBandcamp;
      break;
    case "last.fm":
      icon = faLastfm;
      break;
    case "apple music":
      icon = faApple;
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
      } else if (/twitter/.test(relValue) || /x.com/.test(relValue)) {
        icon = faTwitter;
      } else if (/soundcloud/.test(relValue)) {
        icon = faSoundcloud;
      } else {
        icon = faCircleNodes;
      }
      break;
    default:
      icon = faLink;
      break;
  }
  return (
    <a
      key={relName}
      href={relValue}
      title={relName}
      className="btn btn-icon btn-link"
      target="_blank"
      rel="noopener noreferrer"
    >
      <FontAwesomeIcon icon={icon} fixedWidth />
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
        duration: recording.length,
        release_mbid: recording.release_mbid,
      },
      mbid_mapping: {
        caa_id: recording.caa_id,
        caa_release_mbid: recording.caa_release_mbid,
        recording_mbid: recording.recording_mbid,
        release_mbid: recording.release_mbid,
        artist_mbids: recording.artist_mbids,
      },
    },
  };
}

export async function getArtistCoverImage(
  releaseMBIDs: string[],
  APIURL: string
): Promise<string | undefined> {
  try {
    const payload = {
      background: "transparent",
      image_size: 750,
      dimension: 4,
      "skip-missing": true,
      "show-caa": false,
      tiles: [
        "0,1,4,5",
        "10,11,14,15",
        "2",
        "3",
        "6",
        "7",
        "8",
        "9",
        "12",
        "13",
      ],
      release_mbids: compact(releaseMBIDs),
    };
    const response = await fetch(`${APIURL}/art/grid/`, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json;charset=UTF-8",
      },
    });
    if (response.ok) {
      return await response.text();
    }
  } catch (error) {
    console.error("Could not load image art:", error);
  }
  return undefined;
}
