import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ReleaseCard from "../explore/fresh-releases/components/ReleaseCard";

type AlbumSearchProps = {
  searchQuery: string;
};

type AlbumTypeSearchResult = {
  count: number;
  offset: number;
  "release-groups": {
    id: string;
    title: string;
    "primary-type"?: string;
    "first-release-date"?: string;
    "artist-credit": {
      name: string;
      joinphrase?: string;
      artist: {
        id: string;
        name: string;
      };
    }[];
    releases: {
      id: string;
      title: string;
    }[];
  }[];
};

export default function AlbumSearch(props: AlbumSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-album", searchQuery],
    queryFn: async () => {
      try {
        const queryData = await APIService.albumLookup(searchQuery);
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

  const { data: rawData = {}, hasError = false, errorMessage = "" } =
    loaderData || {};

  const {
    "release-groups": releaseGroups = [],
  } = rawData as AlbumTypeSearchResult;

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
    </>
  );
}
