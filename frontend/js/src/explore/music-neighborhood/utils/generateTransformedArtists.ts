import tinycolor from "tinycolor2";

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
const MAIN_NODE_COLOR = "rgba(53, 48, 112, 1)";

function generateTransformedArtists(
  mainArtist: ArtistNodeInfo,
  similarArtistsList: ArtistNodeInfo[],
  releaseHueSoundColor: tinycolor.Instance,
  recordingHueSoundColor: tinycolor.Instance,
  similarArtistsLimit: number
): GraphDataType {
  const minScore = Math.sqrt(
    similarArtistsList?.[similarArtistsLimit - 1]?.score ?? 0
  );

  const scoreList = similarArtistsList.map(
    (similarArtist: ArtistNodeInfo, index: number) =>
      minScore / Math.sqrt(similarArtist?.score ?? NULL_SCORE)
  );

  const mainArtistNode = {
    id: mainArtist.artist_mbid,
    artist_mbid: mainArtist.artist_mbid,
    artist_name: mainArtist.name,
    size: MAIN_NODE_SIZE,
    color: MAIN_NODE_COLOR,
    score: NULL_SCORE,
  };

  const maximumScore = Math.max(...scoreList);
  const minimumScore = Math.min(...scoreList);

  const similarArtistNodes = similarArtistsList.map((similarArtist, index) => {
    const mixRatio =
      (scoreList[index] - minimumScore) / (maximumScore - minimumScore);
    const computedColor = tinycolor.mix(
      releaseHueSoundColor,
      recordingHueSoundColor,
      mixRatio * 100
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
      (similarArtist: ArtistNodeInfo, index: number): LinkType => {
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
