import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import { useSearchParams } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ListenCard from "../common/listens/ListenCard";
import { getObjectForURLSearchParams } from "../utils/utils";
import Pagination from "../common/Pagination";

const RECORDING_COUNT_PER_PAGE = 50;

type SongSearchProps = {
  searchQuery: string;
};

type SongTypeSearchResult = {
  count: number;
  offset: number;
  recordings: {
    id: string;
    title: string;
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
      "artist-credit": {
        name: string;
        joinphrase?: string;
      }[];
      "release-groups": {
        id: string;
        title: string;
      }[];
    }[];
  }[];
};

export default function SongSearch(props: SongSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-song", searchQuery, currPageNoStr],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * RECORDING_COUNT_PER_PAGE;
        const queryData = await APIService.recordingLookup(
          searchQuery,
          offset,
          RECORDING_COUNT_PER_PAGE
        );
        return {
          data: queryData as SongTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as SongTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as SongTypeSearchResult,
    hasError = false,
    errorMessage = "",
  } = loaderData || {};

  const { recordings = [] } = rawData;
  const totalPageCount = Math.ceil(rawData.count / RECORDING_COUNT_PER_PAGE);

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

  const getListenCard = (recording: SongTypeSearchResult["recordings"][0]) => {
    const artists: MBIDMappingArtist[] = [];
    const artistMBIDs: Array<string> = [];
    const artistCredit = recording["artist-credit"];
    artistCredit.map((ac) => {
      artists.push({
        artist_mbid: ac.artist.id,
        artist_credit_name: ac.name,
        join_phrase: ac.joinphrase ?? "",
      });
      artistMBIDs.push(ac.artist.id);
      return null;
    });

    return (
      <ListenCard
        key={recording.id}
        listen={{
          listened_at: 0,
          track_metadata: {
            mbid_mapping: {
              artists,
              artist_mbids: artistMBIDs,
              release_mbid:
                recording.releases?.length > 0 ? recording.releases[0].id : "",
              recording_mbid: recording.id,
            },
            artist_name: recording["artist-credit"]
              .map((ac) => ac.name + (ac?.joinphrase ?? ""))
              .join(""),
            track_name: recording.title,
            release_name:
              recording.releases?.length > 0 ? recording.releases[0].title : "",
            additional_info: {
              artist_mbids: recording["artist-credit"].map(
                (ac) => ac?.artist?.id
              ),
              recording_mbid: recording.id,
              release_mbid:
                recording.releases?.length > 0 ? recording.releases[0].id : "",
            },
          },
        }}
        showTimestamp={false}
        showUsername={false}
      />
    );
  };

  return (
    <>
      <Loader isLoading={loading} />
      {hasError && <div className="alert alert-danger">{errorMessage}</div>}
      {recordings.length > 0 &&
        recordings.map((recording) => getListenCard(recording))}
      <Pagination
        currentPageNo={currPageNo}
        totalPageCount={totalPageCount}
        handleClickPrevious={handleClickPrevious}
        handleClickNext={handleClickNext}
      />
    </>
  );
}
