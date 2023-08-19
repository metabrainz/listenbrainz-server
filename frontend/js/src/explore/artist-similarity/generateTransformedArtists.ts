import tinycolor from "tinycolor2";
import { ArtistType, GraphDataType, LinkType } from "./Data";

// Serves as the maximum distance between nodes
const LINK_DIST_MULTIPLIER = 250;
// Serves as the minimum distance between nodes
const MIN_LINK_DIST = 0;
// Size of the main node
const MAIN_NODE_SIZE = 150;
// Size of the similar nodes
const SIMILAR_NODE_SIZE = 85;
// Score in case it is undefined (as in case of main artist)
const NULL_SCORE = Infinity;

function generateTransformedArtists(
  mainArtist: ArtistType,
  similarArtistsList: ArtistType[],
  color1: tinycolor.Instance,
  color2: tinycolor.Instance,
  similarArtistsLimit: number
): GraphDataType {
  const minScore = Math.sqrt(
    similarArtistsList?.[similarArtistsLimit - 1]?.score ?? 0
  );
  const scoreList = similarArtistsList.map(
    (similarArtist: ArtistType, index: number) =>
      minScore / Math.sqrt(similarArtist?.score ?? NULL_SCORE)
  );
  const mainArtistNode = {
    id: mainArtist.artist_mbid,
    artist_mbid: mainArtist.artist_mbid,
    artist_name: mainArtist.name,
    size: MAIN_NODE_SIZE,
    color: color1.toRgbString(),
    score: NULL_SCORE,
  };
  const similarArtistNodes = similarArtistsList.map((similarArtist, index) => {
    const computedColor = tinycolor.mix(
      color1,
      color2,
      (index / similarArtistsLimit) * scoreList[index] * 100
    );
    return {
      id: `${similarArtist.artist_mbid}.${mainArtist.artist_mbid}`,
      artist_mbid: similarArtist.artist_mbid,
      artist_name: similarArtist.name,
      size: SIMILAR_NODE_SIZE,
      color: computedColor.toRgbString(),
      score: similarArtist.score ?? NULL_SCORE,
    };
  });

  return {
    nodes: [mainArtistNode, ...similarArtistNodes],
    links: similarArtistsList.map(
      (similarArtist: ArtistType, index: number): LinkType => {
        return {
          source: mainArtist.artist_mbid,
          target:
            similarArtist === mainArtist
              ? mainArtist.artist_mbid
              : `${similarArtist.artist_mbid}.${mainArtist.artist_mbid}`,
          distance: scoreList[index] * LINK_DIST_MULTIPLIER + MIN_LINK_DIST,
        };
      }
    ),
  };
}
export default generateTransformedArtists;
