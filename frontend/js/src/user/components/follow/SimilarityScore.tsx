import * as React from "react";

export type SimilarityScoreProps = {
  type: "regular" | "compact";
  similarityScore: number;
  user?: ListenBrainzUser;
};

const getclassName = (similarityScore: number): string => {
  let className = "";
  if (similarityScore <= 0.15) {
    className = "red";
  } else if (similarityScore <= 0.3) {
    className = "orange";
  } else {
    className = "purple";
  }
  return className;
};

function SimilarityScore(props: SimilarityScoreProps) {
  const { user, type, similarityScore } = props;

  // We transform the similarity score from a scale 0-1 to 0-100
  const percentage = Number((similarityScore * 100).toFixed());
  const className = getclassName(similarityScore);

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
          Your compatibility with {user?.name} is {percentage}%
        </p>
      ) : (
        <p className="small text-muted">{percentage}%</p>
      )}
    </div>
  );
}

export default SimilarityScore;
