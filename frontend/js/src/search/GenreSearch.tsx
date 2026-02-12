import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Link } from "react-router";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";

type GenreSearchResult = {
  gid: string;
  name: string;
};

type GenreSearchProps = {
  searchQuery: string;
};

export default function GenreSearch(props: GenreSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-genre", searchQuery],
    queryFn: async () => {
      try {
        const result = await APIService.searchGenres(searchQuery);
        return {
          data: result.genres,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: [] as GenreSearchResult[],
          hasError: true,
          errorMessage: (error as Error).message,
        };
      }
    },
  });

  const { data: genres = [], hasError = false, errorMessage = "" } =
    loaderData ?? {};

  return (
    <table className="table table-striped table-strong-header">
      <thead>
        <tr>
          <th>{}</th>
          <th>Genre</th>
        </tr>
      </thead>
      <tbody>
        {loading && (
          <tr>
            <td colSpan={2}>
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
            <td colSpan={2}>{errorMessage}</td>
          </tr>
        )}
        {!loading &&
          !hasError &&
          genres.map((genre, index) => (
            <tr key={genre.gid}>
              <td>{index + 1}</td>
              <td>
                <Link to={`/genre/${genre.gid}/`} title={genre.name}>
                  {genre.name}
                </Link>
              </td>
            </tr>
          ))}
        {!loading && !hasError && genres.length === 0 && (
          <tr>
            <td colSpan={2}>No genres found.</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
