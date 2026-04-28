/**
 * Brand icon definitions for music services and social platforms.
 *
 * Icons from Simple Icons (https://simpleicons.org/) are wrapped as
 * FontAwesome-compatible IconDefinition objects so they work with the
 * existing <FontAwesomeIcon> renderer without any type or rendering changes.
 *
 * Icons not available in Simple Icons (Deezer, LinkedIn, Funkwhale, Navidrome)
 * are kept as-is from their original sources.
 */

import {
  IconDefinition,
  IconName,
  IconPrefix,
} from "@fortawesome/fontawesome-svg-core";
import {
  siSpotify,
  siYoutube,
  siSoundcloud,
  siApple,
  siLastdotfm,
  siAmazon,
  siBandcamp,
  siDiscord,
  siFacebook,
  siInstagram,
  siMastodon,
  siNapster,
  siPinterest,
  siSnapchat,
  siTiktok,
  siTwitch,
  siX,
  siVimeo,
  siItunes,
  siInternetarchive,
} from "simple-icons";

// Simple Icons use a 24×24 viewBox
const SI_VIEWBOX = 24;

/** Convert a Simple Icons entry into a FontAwesome-compatible IconDefinition. */
function siToFA(si: {
  slug: string;
  path: string;
}): IconDefinition {
  return {
    prefix: "fab" as IconPrefix,
    iconName: si.slug as IconName,
    icon: [SI_VIEWBOX, SI_VIEWBOX, [], "", si.path],
  };
}

// ---------------------------------------------------------------------------
// Simple-Icons-backed brand icons
// ---------------------------------------------------------------------------

export const brandSpotify = siToFA(siSpotify);
export const brandYoutube = siToFA(siYoutube);
export const brandSoundcloud = siToFA(siSoundcloud);
/** Apple (used for Apple Music) */
export const brandApple = siToFA(siApple);
export const brandLastfm = siToFA(siLastdotfm);
/** iTunes / Apple Music note icon (used for playlist exports) */
export const brandItunes = siToFA(siItunes);
export const brandAmazon = siToFA(siAmazon);
export const brandBandcamp = siToFA(siBandcamp);
export const brandDiscord = siToFA(siDiscord);
export const brandFacebook = siToFA(siFacebook);
export const brandInstagram = siToFA(siInstagram);
export const brandMastodon = siToFA(siMastodon);
export const brandNapster = siToFA(siNapster);
export const brandPinterest = siToFA(siPinterest);
export const brandSnapchat = siToFA(siSnapchat);
export const brandTiktok = siToFA(siTiktok);
export const brandTwitch = siToFA(siTwitch);
/** X (formerly Twitter) */
export const brandX = siToFA(siX);
export const brandVimeo = siToFA(siVimeo);
export const brandInternetArchive = siToFA(siInternetarchive);

// ---------------------------------------------------------------------------
// Icons not available in Simple Icons – kept from original sources
// ---------------------------------------------------------------------------

// Deezer and LinkedIn are not in Simple Icons; keep FontAwesome brands.
export {
  faDeezer,
  faLinkedinIn,
} from "@fortawesome/free-brands-svg-icons";

// Funkwhale and Navidrome have no Simple Icons entry; use custom definitions.
export { faFunkwhale } from "./faFunkwhale";
export { faNavidrome } from "./faNavidrome";
