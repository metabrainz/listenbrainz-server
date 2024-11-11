import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import Username from "../common/Username";

type SearchResultsLoaderData = {
  users: [string, number, number?][];
};

type UserSearchProps = {
  searchQuery: string;
};

export default function UserSearch(props: UserSearchProps) {
  const { searchQuery } = props;

  const { currentUser } = React.useContext(GlobalAppContext);

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-users", searchQuery],
    queryFn: async () => {
      try {
        const queryData = await fetch(window.location.href, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ searchQuery }),
        }).then((res) => res.json());
        return {
          data: queryData as SearchResultsLoaderData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as SearchResultsLoaderData,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const { data: rawData = {}, hasError = false, errorMessage = "" } =
    loaderData || {};

  const { users = [] } = rawData as SearchResultsLoaderData;

  const username = currentUser ? currentUser.name : null;

  return (
    <table className="table table-striped table-strong-header">
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
        {loading && (
          <tr>
            <td colSpan={3}>
              <Loader
                isLoading={loading}
                message="Loading search results..."
                style={{ height: "300px" }}
              />
            </td>
          </tr>
        )}
        {hasError && (
          <tr>
            <td colSpan={3}>{errorMessage}</td>
          </tr>
        )}
        {!loading &&
          !hasError &&
          (users?.length ? (
            users?.map((row, index) => (
              <tr key={`similar-user-${row[0]}`}>
                <td>{index + 1}</td>
                <td>
                  <Username username={row[0]} />
                </td>
                {username && (
                  <td>
                    {(() => {
                      if (username === row[0]) {
                        return "100%, we hope!";
                      }
                      if (row[2]) {
                        return `${(row[2] * 100).toFixed(1)}%`;
                      }
                      return "Similarity score not available";
                    })()}
                  </td>
                )}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={3}>No search results found.</td>
            </tr>
          ))}
      </tbody>
    </table>
  );
}
