/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import { faExclamationCircle, faLink } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { useQuery } from "@tanstack/react-query";
import _ from "lodash";
import Card from "../../../components/Card";
import Loader from "../../../components/Loader";
import Choropleth from "./Choropleth";
import GlobalAppContext from "../../../utils/GlobalAppContext";

export type UserArtistMapProps = {
  range: UserStatsAPIRange;
  user?: ListenBrainzUser;
};

export type UserArtistMapState = {
  data: UserArtistMapData;
  errorMessage?: string;
  hasError?: boolean;
  loading: boolean;
  selectedMetric: "artist" | "listen";
};

export default function UserArtistMap(props: UserArtistMapProps) {
  const { APIService } = React.useContext(GlobalAppContext);

  // Props
  const { user, range } = props;

  const { data: loaderData, isLoading: loading } = useQuery({
    queryKey: ["user-artist-map", range, user?.name],
    queryFn: async () => {
      try {
        const queryData = await APIService.getUserArtistMap(user?.name, range);
        return {
          data: queryData,
          hasError: false,
          errorMessage: "",
        };
      } catch (error) {
        return {
          data: {},
          hasError: true,
          errorMessage: error.message,
        };
      }
    },
  });

  const { data: rawData = {}, hasError = false, errorMessage = "" } =
    loaderData || {};

  const processData = (
    selectedMetric: "artist" | "listen",
    unprocessedData?: UserArtistMapResponse
  ): UserArtistMapData => {
    if (!unprocessedData?.payload) {
      return [];
    }
    return unprocessedData.payload.artist_map.map((country) => {
      return {
        id: country.country,
        value:
          selectedMetric === "artist"
            ? country.artist_count
            : country.listen_count,
        artists: country.artists,
      };
    });
  };

  const [selectedMetric, setSelectedMetric] = React.useState<
    "artist" | "listen"
  >("artist");

  const [data, setData] = React.useState<UserArtistMapData>([]);

  React.useEffect(() => {
    if (rawData && rawData?.payload) {
      const newProcessedData = processData(selectedMetric, rawData);
      setData(newProcessedData);
    }
  }, [rawData, selectedMetric]);

  return (
    <Card className="user-stats-card" data-testid="user-stats-map">
      <div className="d-flex align-items-baseline">
        <div className="d-flex align-items-baseline flex-shrink-1 flex-wrap gap-1">
          <h3 className="capitalize-bold">Artist Origins</h3>
          <small className="hidden-xs">&nbsp;(top 1,000 artists)</small>
        </div>
        <div className="ms-auto">
          <span>Rank by</span>
          <span className="dropdown">
            <button
              className="dropdown-toggle btn-transparent capitalize-bold"
              data-bs-toggle="dropdown"
              type="button"
            >
              {selectedMetric}s
            </button>
            <div className="dropdown-menu" role="menu">
              <button
                type="button"
                onClick={() => setSelectedMetric("listen")}
                className={`dropdown-item ${
                  selectedMetric === "listen" ? "active" : undefined
                }`}
              >
                Listens
              </button>
              <button
                className={`dropdown-item ${
                  selectedMetric === "artist" ? "active" : undefined
                }`}
                type="button"
                onClick={() => setSelectedMetric("artist")}
              >
                Artists
              </button>
            </div>
          </span>
        </div>
        <a
          href="#artist-origin"
          className="btn btn-icon btn-link text-body fs-3"
        >
          <FontAwesomeIcon icon={faLink as IconProp} />
        </a>
      </div>
      <p>Click on a country to see more details</p>
      <Loader isLoading={loading}>
        {hasError ? (
          <div
            className="flex-center"
            style={{
              minHeight: "inherit",
            }}
            data-testid="error-message"
          >
            <span style={{ fontSize: 24 }} className="text-center">
              <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
              {errorMessage}
            </span>
          </div>
        ) : (
          <Choropleth data={data} selectedMetric={selectedMetric} />
        )}
      </Loader>
    </Card>
  );
}
