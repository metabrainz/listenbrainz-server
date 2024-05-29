import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import { useSearchParams } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ReleaseCard from "../explore/fresh-releases/components/ReleaseCard";
import { getObjectForURLSearchParams } from "../utils/utils";
import Pagination from "../common/Pagination";

const ALBUM_COUNT_PER_PAGE = 30;

type AlbumSearchProps = {
  searchQuery: string;
};

export default function AlbumSearch(props: AlbumSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-album", searchQuery, currPageNoStr],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * ALBUM_COUNT_PER_PAGE;
        const queryData = await APIService.albumLookup(
          searchQuery,
          offset,
          ALBUM_COUNT_PER_PAGE
        );
        return {
          data: queryData as AlbumTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as AlbumTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as AlbumTypeSearchResult,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { "release-groups": releaseGroups = [] } = rawData;

  const totalPageCount = Math.ceil(rawData.count / ALBUM_COUNT_PER_PAGE);

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

  const getReleaseCard = (
    releaseGroup: AlbumTypeSearchResult["release-groups"][0]
  ) => {
    const { "artist-credit": artistCredit } = releaseGroup;
    const artistMBIDs: string[] = [];
    artistCredit?.forEach((credit) => {
      const artists = credit.artist;
      if (artists) {
        artistMBIDs.push(artists.id);
      }
    });

    const artistCreditName = artistCredit
      .map((ar) => ar.name + (ar?.joinphrase ?? ""))
      .join("");

    return (
      <ReleaseCard
        key={releaseGroup.id}
        releaseDate={releaseGroup["first-release-date"] ?? undefined}
        dateFormatOptions={{ year: "numeric", month: "short" }}
        releaseGroupMBID={releaseGroup.id}
        releaseName={releaseGroup.title}
        caaID={null}
        caaReleaseMBID={null}
        releaseTypePrimary={releaseGroup["primary-type"] ?? ""}
        artistCreditName={artistCreditName}
        artistMBIDs={artistMBIDs}
        showInformation
        showArtist
        showReleaseTitle
        showListens
      />
    );
  };

  return (
    <>
      <Loader isLoading={loading} />
      {hasError && <div className="alert alert-danger">{errorMessage}</div>}
      {!loading && !hasError && (
        <div className="release-cards-grid">
          {releaseGroups?.map((releaseGroup) => getReleaseCard(releaseGroup))}
        </div>
      )}
      <Pagination
        currentPageNo={currPageNo}
        totalPageCount={totalPageCount}
        handleClickPrevious={handleClickPrevious}
        handleClickNext={handleClickNext}
      />
    </>
  );
}
