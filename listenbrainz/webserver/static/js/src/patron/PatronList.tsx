import { groupBy } from "lodash";
import * as React from "react";

const PatronList = ({ patrons }: { patrons: Array<String> }) => {
  const patronGroups = [];
  for (let i = 0; i < patrons.length; i += 4) {
    const group = [];
    for (let j = 0; j < 4; j += 1) {
      group.push(patrons[i + j]);
    }
    patronGroups.push(group);
  }

  const renderUsername = (username: String) => {
    if (!username) return "";
    return (
      <div className="col-md-3" style={{ textAlign: "center" }}>
        <h4>
          <span role="img" aria-label="headphone emoji">
            🎧
          </span>{" "}
          <a href={`https://listenbrainz.org/user/${username}`}>{username}</a>
        </h4>
      </div>
    );
  };

  return (
    <>
      {patronGroups.map((group) => {
        return (
          <>
            <div className="row">{group.map(renderUsername)}</div>
            <br />
          </>
        );
      })}
    </>
  );
};

export default PatronList;
