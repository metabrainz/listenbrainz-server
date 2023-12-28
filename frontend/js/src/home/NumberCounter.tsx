import * as React from "react";

type NumberCounterProps = {
  count: number;
};

function NumberCounter({ count }: NumberCounterProps) {
  const countString = count.toString();
  const reversedStr = countString.split("").reverse().join("");
  const groupsOfThree = reversedStr.match(/\d{1,3}/g);
  const reversedGroupsOfCount = groupsOfThree ? groupsOfThree.reverse() : [];

  return (
    <div className="number-count">
      {reversedGroupsOfCount.map((group, idx) => {
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
