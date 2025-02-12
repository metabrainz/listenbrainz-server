import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import { useSearchParams } from "react-router-dom";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ListenCard from "../common/listens/ListenCard";
import {
  getArtistLink,
  getObjectForURLSearchParams,
  getTrackLink,
} from "../utils/utils";
import Pagination from "../common/Pagination";
import { millisecondsToStr } from "../playlists/utils";

const RECORDING_COUNT_PER_PAGE = 50;

type TrackSearchProps = {
  searchQuery: string;
};

export default function TrackSearch(props: TrackSearchProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObj = getObjectForURLSearchParams(searchParams);
  const currPageNoStr = searchParams.get("page") || "1";
  const currPageNo = parseInt(currPageNoStr, 10);

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-track", searchQuery, currPageNoStr],
    queryFn: async () => {
      try {
        const offset = (currPageNo - 1) * RECORDING_COUNT_PER_PAGE;
        const queryData = await APIService.recordingLookup(
          searchQuery,
          offset,
          RECORDING_COUNT_PER_PAGE
        );
        return {
          data: queryData as TrackTypeSearchResult,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {} as TrackTypeSearchResult,
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const {
    data: rawData = {} as TrackTypeSearchResult,
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

  const getListenCard = (recording: TrackTypeSearchResult["recordings"][0]) => {
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

    const artistName = artistCredit
      .map((ac) => ac.name + (ac?.joinphrase ?? ""))
      .join("");

    const listen: Listen = {
      listened_at: 0,
      track_metadata: {
        mbid_mapping: {
          artists,
          artist_mbids: artistMBIDs,
          release_mbid:
            recording.releases?.length > 0 ? recording.releases[0].id : "",
          recording_mbid: recording.id,
        },
        artist_name: artistName,
        track_name: recording.title,
        release_name:
          recording.releases?.length > 0 ? recording.releases[0].title : "",
        additional_info: {
          artist_mbids: artistMBIDs,
          recording_mbid: recording.id,
          duration_ms: recording.length,
          release_mbid:
            recording.releases?.length > 0 ? recording.releases[0].id : "",
        },
      },
    };

    /* Copied over from ListenCard component. Required to show disambiguation as there is
    no such field in the Listen type to implement it directly in ListenCard component */
    const listenDetails = (
      <>
        <div className="title-duration">
          <div title={recording.title} className="ellipsis-2-lines">
            {getTrackLink(listen)}
            {recording.disambiguation?.length && (
              <span className="small text-muted">
                {" "}
                ({recording.disambiguation})
              </span>
            )}
          </div>
          {recording.length && (
            <div className="small text-muted" title="Duration">
              {millisecondsToStr(recording.length)}
            </div>
          )}
        </div>
        <div className="small text-muted ellipsis" title={artistName}>
          {getArtistLink(listen)}
        </div>
      </>
    );

    return (
      <ListenCard
        key={recording.id}
        listen={listen}
        showTimestamp={false}
        showUsername={false}
        listenDetails={listenDetails}
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
