import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Helmet } from "react-helmet";
import { useLocation } from "react-router-dom";
import { RouteQuery } from "../../utils/Loader";
import Username from "../../common/Username";
import FlairsExplanationButton from "../../common/flairs/FlairsExplanationButton";

export default function SimilarUsers() {
  const location = useLocation();
  const { data } = useQuery<{ similarUsers: string[][] }>(
    RouteQuery(["similar-users"], location.pathname)
  );
  const { similarUsers } = data || {};

  return (
    <div id="similar-users" role="main">
      <Helmet>
        <title>Top Similar Users</title>
      </Helmet>
      <h2 className="page-title">Top Similar Users</h2>

      <p>
        Below is a list of the top similar users and how similar they are.
        Sometimes this page can show bugs in how we calculate similar users, but
        more often it can show that some of our users are behaving in naughty
        ways: Sockpuppet accounts and listen spammers. This page should help us
        find these bad actors and let us report them.
      </p>

      <FlairsExplanationButton />

      <table className="table table-striped">
        <tbody>
          {similarUsers?.length ? (
            similarUsers?.map((row, index) => (
              <tr>
                <td>
                  <Username username={row[0]} />
                </td>
                <td>
                  <Username username={row[1]} />
                </td>
                <td>{row[2]}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td>No similar users to show.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
