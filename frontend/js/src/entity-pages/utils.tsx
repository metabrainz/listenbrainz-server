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
