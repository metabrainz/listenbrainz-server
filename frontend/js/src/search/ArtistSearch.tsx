import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import { Link, useSearchParams } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import { getObjectForURLSearchParams } from "../utils/utils";
import Pagination from "../common/Pagination";

const ARTIST_COUNT_PER_PAGE = 50;

type ArtistSearchProps = {
  searchQuery: string;
};

export default function ArtistSearch(props: ArtistSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-artist", searchQuery, currPageNoStr],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * ARTIST_COUNT_PER_PAGE;
        const queryData = await APIService.artistLookup(
          searchQuery,
          offset,
          ARTIST_COUNT_PER_PAGE
        );
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

  const {
    data: rawData = {} as ArtistTypeSearchResult,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { artists = [] } = rawData;
  const totalPageCount = Math.ceil(rawData.count / ARTIST_COUNT_PER_PAGE);

  const handleClickPrevious = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.max(currPageNo - 1, 1).toString(),
    });
  };

  const handleClickNext = () => {
    setSearchParams({
      ...searchParamsObj,
      page: Math.min(currPageNo + 1, totalPageCount).toString(),
    });
  };

  return (
    <>
      <table className="table table-striped table-strong-header">
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
                <td>{(currPageNo - 1) * ARTIST_COUNT_PER_PAGE + index + 1}</td>
                <td>
                  <Link
                    to={`/artist/${artist?.id}/`}
                    title={`(${artist["sort-name"]}${
                      artist?.disambiguation ? `, ${artist.disambiguation}` : ""
                    })`}
                  >
                    {artist?.name}
                  </Link>
                  {artist?.disambiguation && (
                    <small>&nbsp;({artist.disambiguation})</small>
                  )}
                </td>
                <td>{artist?.type}</td>
                <td>{_.capitalize(artist?.gender)}</td>
                <td>{artist?.area?.name}</td>
              </tr>
            ))}
        </tbody>
      </table>
      <Pagination
        currentPageNo={currPageNo}
        totalPageCount={totalPageCount}
        handleClickPrevious={handleClickPrevious}
        handleClickNext={handleClickNext}
      />
    </>
  );
}
