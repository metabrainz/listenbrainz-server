import * as React from "react";
import { useLoaderData, useNavigate } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";

type SearchResultsLoaderData = {
  searchTerm: string;
  users: [string, number, number?][];
};

export default function SearchResults() {
  const navigate = useNavigate();
  const { searchTerm, users } = useLoaderData() as SearchResultsLoaderData;
  const { currentUser } = React.useContext(GlobalAppContext);

  const [searchTermInput, setSearchTermInput] = React.useState(searchTerm);
  const username = currentUser ? currentUser.name : null;

  const search = () => {
    if (!searchTermInput) {
      return;
    }
    navigate(`/search/?search_term=${searchTermInput}`);
  };

  return (
    <>
      <div className="form-group row">
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
              onClick={search}
            >
              Search Again!
            </button>
          </span>
        </div>
      </div>

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
          {users.length > 0 ? (
            users.map((row, index) => (
              <tr key={`similar-user-${row[0]}`}>
                <td>{index + 1}</td>
                <td>
                  <a href={`/user/${row[0]}/`}>{row[0]}</a>
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
              <td colSpan={username ? 3 : 2}>No search results found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </>
  );
}
