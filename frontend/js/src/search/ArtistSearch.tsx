import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import { Link } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";

type ArtistSearchProps = {
  searchQuery: string;
};

type ArtistTypeSearchResult = {
  count: number;
  offset: number;
  artists: {
    name: string;
    id: string;
    type?: string;
    country?: string;
    gender?: string;
    area?: {
      name: string;
    };
  }[];
};

export default function ArtistSearch(props: ArtistSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-artist", searchQuery],
    queryFn: async () => {
      try {
        const queryData = await APIService.artistLookup(searchQuery);
        return {
          data: queryData as ArtistTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as ArtistTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const { data: rawData = {}, hasError = false, errorMessage = "" } =
    loaderData || {};

  const { artists = [] } = rawData as ArtistTypeSearchResult;

  return (
    <table className="table table-striped">
      <thead>
        <tr>
          <th>{}</th>
          <th>Name</th>
          <th>Type</th>
          <th>Gender</th>
          <th>Area</th>
        </tr>
      </thead>
      <tbody>
        {loading && (
          <tr>
            <td colSpan={5}>
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
            <td colSpan={5}>{errorMessage}</td>
          </tr>
        )}
        {!loading &&
          !hasError &&
          artists.map((artist, index) => (
            <tr key={artist?.id}>
              <td>{index + 1}</td>
              <td>
                <Link to={`/artist/${artist?.id}/`}>{artist?.name}</Link>
              </td>
              <td>{artist?.type}</td>
              <td>{_.capitalize(artist?.gender)}</td>
              <td>{artist?.area?.name}</td>
            </tr>
          ))}
      </tbody>
    </table>
  );
}
