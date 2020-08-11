import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import APIService from "../APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";
import Choropleth from "./Choropleth";

export type UserArtistMapProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserArtistMapState = {
  loading: boolean;
  hasError?: boolean;
  errorMessage?: string;
  data: UserArtistMapData;
  graphContainerWidth?: number;
};

export default class UserArtistMap extends React.Component<
  UserArtistMapProps,
  UserArtistMapState
> {
  APIService: APIService;

  graphContainer: React.RefObject<HTMLDivElement>;

  constructor(props: UserArtistMapProps) {
    super(props);
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: [],
      loading: false,
      errorMessage: "",
      hasError: false,
    };

    this.graphContainer = React.createRef();
  }

  componentDidMount() {
    window.addEventListener("resize", this.handleResize);

    this.handleResize();
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

  componentWillUnmount() {
    window.removeEventListener("resize", this.handleResize);
  }

  loadData = async (): Promise<void> => {
    this.setState({
      hasError: false,
      loading: true,
    });
    const data = await this.getData();
    this.setState({
      data: this.processData(data),
      loading: false,
    });
  };

  getData = async (): Promise<UserArtistMapResponse> => {
    const { range, user } = this.props;
    try {
      const data = await this.APIService.getUserArtistMap(user.name, range);
      return data;
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
    return {} as UserArtistMapResponse;
  };

  processData = (data: UserArtistMapResponse): UserArtistMapData => {
    return data.payload.artist_map.map((country) => {
      return {
        id: country.country,
        value: country.artist_count,
      };
    });
  };

  handleResize = () => {
    this.setState({
      graphContainerWidth: this.graphContainer.current?.offsetWidth,
    });
  };

  render() {
    const {
      loading,
      hasError,
      errorMessage,
      data,
      graphContainerWidth,
    } = this.state;

    return (
      <Card
        style={{
          marginTop: 20,
          minHeight: (graphContainerWidth || 1200) * 0.5,
        }}
        ref={this.graphContainer}
      >
        <div className="row">
          <div className="col-xs-12">
            <h3 className="capitalize-bold" style={{ marginLeft: 20 }}>
              Artist Origins
            </h3>
          </div>
        </div>
        <Loader isLoading={loading}>
          {hasError && (
            <div
              className="flex-center"
              style={{
                minHeight: "inherit",
              }}
            >
              <span style={{ fontSize: 24 }} className="text-center">
                <FontAwesomeIcon icon={faExclamationCircle as IconProp} />{" "}
                {errorMessage}
              </span>
            </div>
          )}
          {!hasError && (
            <div className="row">
              <div className="col-xs-12">
                <Choropleth data={data} width={graphContainerWidth} />
              </div>
            </div>
          )}
        </Loader>
      </Card>
    );
  }
}
