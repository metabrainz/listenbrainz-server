import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import _ from "lodash";
import GlobalAppContext from "../utils/GlobalAppContext";
import Loader from "../components/Loader";
import ListenCard from "../common/listens/ListenCard";

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

  const { searchQuery } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["search-song", searchQuery],
    queryFn: async () => {
      try {
        const queryData = await APIService.recordingLookup(searchQuery);
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

  const { data: rawData = {}, hasError = false, errorMessage = "" } =
    loaderData || {};

  const { recordings = [] } = rawData as SongTypeSearchResult;

  return (
    <>
      <Loader isLoading={loading} />
      {hasError && <div className="alert alert-danger">{errorMessage}</div>}
      {recordings.length > 0 &&
        recordings.map((recording) => (
          <ListenCard
            key={recording.id}
            listen={{
              listened_at: 0,
              track_metadata: {
                artist_name: recording["artist-credit"]
                  .map((ac) => ac.name + (ac?.joinphrase ?? ""))
                  .join(""),
                track_name: recording.title,
                release_name:
                  recording.releases?.length > 0
                    ? recording.releases[0].title
                    : "",
                additional_info: {
                  artist_mbids: recording["artist-credit"].map(
                    (ac) => ac?.artist?.id
                  ),
                  recording_mbid: recording.id,
                  release_mbid:
                    recording.releases?.length > 0
                      ? recording.releases[0].id
                      : "",
                },
              },
            }}
            showTimestamp={false}
            showUsername={false}
          />
        ))}
    </>
  );
}
