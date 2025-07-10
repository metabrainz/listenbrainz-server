import tinycolor from "tinycolor2";

// Serves as the maximum distance between nodes
const LINK_DIST_MULTIPLIER = 250;
// Serves as the minimum distance between nodes
const MIN_LINK_DIST = 0;
// Size of the main node
const MAIN_NODE_SIZE = 150;
// Size of the similar nodes
const SIMILAR_NODE_SIZE = 85;
// Score in case it is undefined (as in case of main recording)
const NULL_SCORE = Infinity;
const MAIN_NODE_COLOR = "rgba(53, 48, 112, 1)";

function generateTransformedRecordings(
  mainRecording: RecordingNodeInfo,
  similarRecordingsList: RecordingNodeInfo[],
  releaseHueSoundColor: tinycolor.Instance,
  recordingHueSoundColor: tinycolor.Instance,
  similarRecordingsLimit: number
): RecordingGraphDataType {
  const minScore = Math.sqrt(
    similarRecordingsList?.[similarRecordingsLimit - 1]?.score ?? 0
  );

  const scoreList = similarRecordingsList.map(
    (similarRecording: RecordingNodeInfo, index: number) =>
      minScore / Math.sqrt(similarRecording?.score ?? NULL_SCORE)
  );

  const mainRecordingNode = {
    id: mainRecording.recording_mbid,
    recording_mbid: mainRecording.recording_mbid,
    recording_name: mainRecording.recording_name,
    size: MAIN_NODE_SIZE,
    color: MAIN_NODE_COLOR,
    score: NULL_SCORE,
  };

  const maximumScore = Math.max(...scoreList);
  const minimumScore = Math.min(...scoreList);

  const similarRecordingNodes = similarRecordingsList.map(
    (similarRecording, index) => {
      const mixRatio =
        (scoreList[index] - minimumScore) / (maximumScore - minimumScore);
      const computedColor = tinycolor.mix(
        releaseHueSoundColor,
        recordingHueSoundColor,
        mixRatio * 100
      );

      return {
        id: `${similarRecording.recording_mbid}.${mainRecording.recording_mbid}`,
        recording_mbid: similarRecording.recording_mbid,
        recording_name: similarRecording.recording_name,
        size: SIMILAR_NODE_SIZE,
        color: computedColor.toRgbString(),
        score: similarRecording.score ?? NULL_SCORE,
      };
    }
  );

  return {
    nodes: [mainRecordingNode, ...similarRecordingNodes],
    links: similarRecordingsList.map(
      (similarRecording: RecordingNodeInfo, index: number): LinkType => {
        return {
          source: mainRecording.recording_mbid,
          target:
            similarRecording === mainRecording
              ? mainRecording.recording_mbid
              : `${similarRecording.recording_mbid}.${mainRecording.recording_mbid}`,
          distance: scoreList[index] * LINK_DIST_MULTIPLIER + MIN_LINK_DIST,
        };
      }
    ),
  };
}

export default generateTransformedRecordings;
