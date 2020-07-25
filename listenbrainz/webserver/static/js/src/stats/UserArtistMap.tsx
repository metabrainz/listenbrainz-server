import * as React from "react";
import { ResponsiveChoropleth } from "@nivo/geo";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import * as features from "./world_countries.json";
import * as alpha2To3Map from "./alpha_2_to_3_map.json";

const DATASET_HOSTER_URL = "http://bono.metabrainz.org:5000";

export type UserArtistMapProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistMapState = {
  loading: boolean;
  hasError?: boolean;
  errorMessage?: string;
  data: Array<{ id: string; value: number }>;
};

export default class UserArtistMap extends React.Component<
  UserArtistMapProps,
  UserArtistMapState
> {
  APIService: APIService;

  constructor(props: UserArtistMapProps) {
    super(props);
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      loading: false,
      data: [],
    };
  }

  componentDidUpdate(prevProps: UserArtistMapProps) {
    const { range: prevRange } = prevProps;
    const { range: currRange } = this.props;
    if (prevRange !== currRange) {
      if (["week", "month", "year", "all_time"].indexOf(currRange) < 0) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: `Invalid range: ${currRange}`,
        });
      } else {
        this.loadData();
      }
    }
  }

  loadData = async () => {
    this.setState({
      hasError: false,
      loading: true,
    });
    const data = await this.getData();
    this.setState({
      data,
      loading: false,
    });
  };

  getData = async () => {
    const { range, user } = this.props;
    try {
      const data = await this.APIService.getUserArtistMapData(user.name, range);
      console.log(data);
      return data.payload.country_code_data;
    } catch (error) {
      if (error.response && error.response.status === 204) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
        });
      } else {
        this.setState(() => {
          throw error;
        });
      }
    }
    return {};
  };

  render() {
    const { loading, hasError, errorMessage, data } = this.state;

    return (
      <div>
        <Card style={{ minHeight: 400 }}>
          <Loader
            isLoading={loading}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "inherit",
            }}
          >
            <div className="row">
              <div className="col-xs-12" style={{ height: 700 }}>
                {hasError && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minHeight: "inherit",
                    }}
                  >
                    <span style={{ fontSize: 24 }}>
                      <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                      {errorMessage}
                    </span>
                  </div>
                )}
                {!hasError && (
                  <ResponsiveChoropleth
                    data={data}
                    features={features.features}
                    margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
                    colors="oranges"
                    domain={[0, 50]}
                    unknownColor="#666666"
                    label="properties.name"
                    valueFormat=".2s"
                    projectionTranslation={[0.5, 0.5]}
                    projectionRotation={[0, 0, 0]}
                    enableGraticule
                    graticuleLineColor="#dddddd"
                    borderWidth={0.5}
                    borderColor="#152538"
                    legends={[
                      {
                        anchor: "bottom-left",
                        direction: "column",
                        justify: true,
                        translateX: 20,
                        translateY: -100,
                        itemsSpacing: 0,
                        itemWidth: 94,
                        itemHeight: 18,
                        itemDirection: "left-to-right",
                        itemTextColor: "#444444",
                        itemOpacity: 0.85,
                        symbolSize: 18,
                        effects: [
                          {
                            on: "hover",
                            style: {
                              itemTextColor: "#000000",
                              itemOpacity: 1,
                            },
                          },
                        ],
                      },
                    ]}
                  />
                )}
              </div>
            </div>
          </Loader>
        </Card>
      </div>
    );
  }
}
