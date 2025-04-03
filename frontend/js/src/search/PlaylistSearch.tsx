import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import { getObjectForURLSearchParams } from "../utils/utils";
import Pagination from "../common/Pagination";

const PLAYLIST_COUNT_PER_PAGE = 25;

type PlayListSearchProps = {
  searchQuery: string;
};

export default function PlaylistSearch(props: PlayListSearchProps) {
  const { searchQuery } = props;

  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: [
      "search-playlist",
      searchQuery,
      currPageNoStr,
      currentUser?.name,
    ],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * PLAYLIST_COUNT_PER_PAGE;
        let queryData;
        if (currentUser?.name) {
          queryData = await APIService.searchPlaylistsForUser(
            searchQuery,
            currentUser.name,
            PLAYLIST_COUNT_PER_PAGE,
            offset
          );
        } else {
          queryData = await APIService.searchPlaylists(
            searchQuery,
            PLAYLIST_COUNT_PER_PAGE,
            offset
          );
        }
        return {
          data: queryData as PlaylistTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as PlaylistTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as PlaylistTypeSearchResult,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { playlists = [] } = rawData;
  const totalPageCount = Math.ceil(
    rawData.playlist_count / PLAYLIST_COUNT_PER_PAGE
  );

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
            <th>Title</th>
            <th>Description</th>
            <th>Creator</th>
            <th>Date of creation</th>
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
            playlists.map((playlist_, index) => {
              const { playlist } = playlist_;

              const playListID =
                playlist.identifier.match(/([a-f0-9-]{36})$/)?.[0] || "";

              const playlistDate = new Date(
                playlist?.date
              )?.toLocaleDateString();

              return (
                <tr key={playListID}>
                  <td>
                    {(currPageNo - 1) * PLAYLIST_COUNT_PER_PAGE + index + 1}
                  </td>
                  <td>
                    <Link to={`/playlist/${playListID}/`}>
                      {playlist.title}
                    </Link>
                  </td>
                  <td
                    className="ellipsis-4-lines"
                    // eslint-disable-next-line react/no-danger
                    dangerouslySetInnerHTML={{
                      __html: playlist?.annotation || "",
                    }}
                  />
                  <td>
                    <Link
                      to={`https://musicbrainz.org/user/${playlist?.creator}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {playlist.creator}
                    </Link>
                  </td>
                  <td>{playlistDate}</td>
                </tr>
              );
            })}
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
