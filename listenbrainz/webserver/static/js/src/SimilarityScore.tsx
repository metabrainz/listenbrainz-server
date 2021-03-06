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
  const { similarityScore, user, type } = props;
  const className = getclassName(similarityScore);

  return (
    <div className={`similarity-score ${type}`}>
      <div
        className="progress"
        aria-label="Similarity Score"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={similarityScore * 100}
        tabIndex={0}
      >
        <div
          className={`progress-bar ${className}`}
          style={{
            width: `${similarityScore * 100}%`,
          }}
        />
      </div>
      {type === "regular" ? (
        <p className="text-muted">
          Your compatibility with {user?.name} is {similarityScore * 10}/10
        </p>
      ) : (
        <p className="small text-muted">{similarityScore * 10}/10</p>
      )}
    </div>
  );
};

export default SimilarityScore;
