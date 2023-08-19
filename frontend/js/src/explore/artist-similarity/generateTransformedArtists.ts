import tinycolor from "tinycolor2";
import { ArtistType, GraphDataType, LinkType, NodeType } from "./Data";

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
  const scoreList: Array<number> = [];

  let minScore = similarArtistsList?.[similarArtistsLimit - 1]?.score ?? 0;
  minScore = Math.sqrt(minScore);

  const transformedArtists: GraphDataType = {
    nodes: [mainArtist, ...similarArtistsList].map(
      (similarArtist: ArtistType, index: number): NodeType => {
        let computedScore;
        let computedColor;
        if (similarArtist !== mainArtist) {
          computedScore =
            minScore / Math.sqrt(similarArtist?.score ?? NULL_SCORE);
          computedColor = tinycolor.mix(
            color1,
            color2,
            (index / similarArtistsLimit) * computedScore * 100
          );
          scoreList.push(computedScore);
        } else {
          let remaining;
          [computedColor, ...remaining] = [color1, color2];
        }
        return {
          id:
            similarArtist === mainArtist
              ? mainArtist.artist_mbid
              : `${similarArtist.artist_mbid}.${mainArtist.artist_mbid}`,
          artist_mbid: similarArtist.artist_mbid,
          artist_name: similarArtist.name,
          size:
            similarArtist.artist_mbid === mainArtist?.artist_mbid
              ? MAIN_NODE_SIZE
              : SIMILAR_NODE_SIZE,
          color: computedColor.toRgbString(),
          score: similarArtist.score ?? NULL_SCORE,
        };
      }
    ),
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

  return transformedArtists;
}
export default generateTransformedArtists;
