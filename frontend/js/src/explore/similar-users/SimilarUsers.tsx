import * as React from "react";
import { Helmet } from "react-helmet";
import { Link, useLoaderData } from "react-router-dom";

export default function SimilarUsers() {
  const { similarUsers } = useLoaderData() as { similarUsers: string[][] };
  return (
    <div id="similar-users">
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

      <table className="table table-striped">
        <tbody>
          {similarUsers.length > 0 ? (
            similarUsers.map((row, index) => (
              <tr>
                <td>
                  <Link to={`/user/${row[0]}/`}>{row[0]}</Link>
                </td>
                <td>
                  <Link to={`/user/${row[1]}/`}>{row[1]}</Link>
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
