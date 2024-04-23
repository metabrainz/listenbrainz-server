import * as React from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";
import { RouteQuery } from "../utils/Loader";
import { getObjectForURLSearchParams } from "../utils/utils";

type SearchResultsLoaderData = {
  users: [string, number, number?][];
};

export default function SearchResults() {
  const { currentUser } = React.useContext(GlobalAppContext);

  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const { data } = useQuery<SearchResultsLoaderData>(
    RouteQuery(
      ["search-users", getObjectForURLSearchParams(searchParams)],
      location.pathname
    )
  );
  const { users } = data || {};

  const [searchTermInput, setSearchTermInput] = React.useState(
    searchParams.get("search_term") || ""
  );
  const username = currentUser ? currentUser.name : null;

  const search = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!searchTermInput) {
      return;
    }
    setSearchParams({ search_term: searchTermInput });
  };

  return (
    <>
      <form className="form-group row" onSubmit={search}>
        <h2 className="col-sm-4">Username Search Results</h2>
        <div className="col-xs-6">
          <input
            type="text"
            className="form-control"
            name="search_term"
            placeholder="Not found yet?"
            value={searchTermInput}
            style={{ marginTop: "25px" }}
            onChange={(e) => setSearchTermInput(e.target.value)}
            required
          />
        </div>
        <div className="col-xs-2">
          <span className="input-group-btn">
            <button
              className="btn btn-default"
              type="submit"
              style={{ marginTop: "27px" }}
            >
              Search Again!
            </button>
          </span>
        </div>
      </form>

      <table className="table table-striped">
        <thead>
          <tr>
            <th>{}</th>
            <th>User</th>
            {username && (
              <th>
                Similarity to you{" "}
                <span
                  className="glyphicon glyphicon-question-sign"
                  title="Similarity between users is calculated based on their listen history."
                />
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {users?.length ? (
            users?.map((row, index) => (
              <tr key={`similar-user-${row[0]}`}>
                <td>{index + 1}</td>
                <td>
                  <Link to={`/user/${row[0]}/`}>{row[0]}</Link>
                </td>
                {username && (
                  <td>
                    {(() => {
                      if (username === row[0]) {
                        return "100%, we hope!";
                      }
                      if (row[2]) {
                        return `${(row[2] * 10).toFixed(1)}%`;
                      }
                      return "Similarity score not available";
                    })()}
                  </td>
                )}
              </tr>
            ))
          ) : (
            <tr>
              <td>No search results found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
