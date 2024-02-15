import * as React from "react";

type NumberCounterProps = {
  count: number;
};

function NumberCounter({ count }: NumberCounterProps) {
  const countString = count?.toString();
  const groupsOfThree = countString?.match(/(\d+?)(?=(\d{3})+(?!\d)|$)/g) ?? [];

  return (
    <div className="number-count">
      {groupsOfThree.map((group, idx) => {
        return (
          <div
            key={`listen-group-${idx.toString()}`}
            className="number-count-group"
          >
            {group.split("").map((digit, digitIndex) => (
              <span
                key={`listen-digit-${idx.toString()}-${digitIndex.toString()}`}
                className="number-count-digit"
              >
                {digit}
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );
}

export default NumberCounter;
