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
import { COLOR_BLACK } from "../../../utils/constants";
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
      <div className="row">
        <div className="col-md-9 col-xs-6">
          <h3 style={{ marginLeft: 20 }}>
            <span className="capitalize-bold">Artist Origins</span>
            <small>&nbsp;Click on a country to see more details</small>
          </h3>
        </div>
        <div className="col-md-2 col-xs-4 text-right" style={{ marginTop: 20 }}>
          <span>Rank by</span>
          <span className="dropdown">
            <button
              className="dropdown-toggle btn-transparent capitalize-bold"
              data-toggle="dropdown"
              type="button"
            >
              {selectedMetric}s
              <span className="caret" />
            </button>
            <ul className="dropdown-menu" role="menu">
              <li
                className={selectedMetric === "listen" ? "active" : undefined}
              >
                <button
                  type="button"
                  onClick={() => setSelectedMetric("listen")}
                >
                  Listens
                </button>
              </li>
              <li
                className={selectedMetric === "artist" ? "active" : undefined}
              >
                <button
                  type="button"
                  onClick={() => setSelectedMetric("artist")}
                >
                  Artists
                </button>
              </li>
            </ul>
          </span>
        </div>
        <div className="col-md-1 col-xs-2 text-right">
          <h4 style={{ marginTop: 20 }}>
            <a href="#artist-origin">
              <FontAwesomeIcon
                icon={faLink as IconProp}
                size="sm"
                color={COLOR_BLACK}
                style={{ marginRight: 20 }}
              />
            </a>
          </h4>
        </div>
      </div>
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
