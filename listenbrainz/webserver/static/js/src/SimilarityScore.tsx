import * as React from "react";

export type SimilarityScoreProps = {
  type: "regular" | "compact";
  similarityScore: number;
  user?: ListenBrainzUser;
};

const getclassName = (similarityScore: number): string => {
  let className = "";
  if (similarityScore <= 0.3) {
    className = "red";
  } else if (similarityScore <= 0.7) {
    className = "orange";
  } else {
    className = "purple";
  }
  return className;
};

const SimilarityScore = (props: SimilarityScoreProps) => {
  const { user, type, similarityScore } = props;

  // We transform the similarity score from a scale 0-1 to 0-10
  const adjustedSimilarityScore = Number((similarityScore * 10).toFixed(1));
  const className = getclassName(similarityScore);
  const percentage = adjustedSimilarityScore * 10;

  return (
    <div
      className={`similarity-score ${type}`}
      title="Your similarity score with that user"
    >
      <div
        className="progress"
        aria-label="Similarity score"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percentage}
        tabIndex={0}
      >
        <div
          className={`progress-bar ${className}`}
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
      {type === "regular" ? (
        <p className="text-muted">
          Your compatibility with {user?.name} is {adjustedSimilarityScore}
          /10
        </p>
      ) : (
        <p className="small text-muted">{adjustedSimilarityScore}/10</p>
      )}
    </div>
  );
};

export default SimilarityScore;
