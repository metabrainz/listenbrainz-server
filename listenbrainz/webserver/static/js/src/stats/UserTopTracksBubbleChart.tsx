/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

import { ResponsiveCirclePacking } from "@nivo/circle-packing";
import APIService from "../APIService";
import Card from "../components/Card";
import Loader from "../components/Loader";

import * as circleData from "./circlePacking.json";

export type UserTopTracksBubbleProps = {
  range: UserStatsAPIRange;
  user: ListenBrainzUser;
  apiUrl: string;
};

export type UserTopTracksBubbleState = {
  data: UserTopTracksBubbleResponse;
  errorMessage?: string;
  graphContainerWidth?: number;
  hasError?: boolean;
  loading: boolean;
};

export default class UserTopTracksBubble extends React.Component<
  UserTopTracksBubbleProps,
  UserTopTracksBubbleState
> {
  APIService: APIService;

  graphContainer: React.RefObject<HTMLDivElement>;

  properties: any;

  constructor(props: UserTopTracksBubbleProps) {
    super(props);
    this.APIService = new APIService(
      props.apiUrl || `${window.location.origin}/1`
    );

    this.state = {
      data: {} as UserTopTracksBubbleResponse,
      loading: false,
      errorMessage: "",
      hasError: false,
    };

    this.graphContainer = React.createRef();

    this.properties = {
      height: 500,
      padding: 2,
      id: "name",
      value: "listen_count",
      labelsSkipRadius: 16,
    };
  }

  componentDidMount() {
    window.addEventListener("resize", this.handleResize);

    this.handleResize();
  }

  componentDidUpdate(prevProps: UserTopTracksBubbleProps) {
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
    const rawData = await this.getData();
    this.setState({
      data: rawData,
      loading: false,
    });
  };

  getData = async (): Promise<UserTopTracksBubbleResponse> => {
    const { range, user } = this.props;
    try {
      return await this.APIService.getUserTopTracksBubble(user.name, range);
    } catch (error) {
      if (error.response && error.response.status === 204) {
        this.setState({
          loading: false,
          hasError: true,
          errorMessage: "Statistics for the user have not been calculated",
        });
      } else {
        throw error;
      }
    }
    return {} as UserTopTracksBubbleResponse;
  };

  handleResize = () => {
    this.setState({
      graphContainerWidth: this.graphContainer.current?.offsetWidth,
    });
  };

  render() {
    const {
      data,
      errorMessage,
      graphContainerWidth,
      hasError,
      loading,
    } = this.state;

    return (
      <Card
        style={{
          marginTop: 20,
          minHeight: (graphContainerWidth || 1200) * 0.5,
        }}
        ref={this.graphContainer}
      >
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
            <div
              className="row"
              style={{
                marginTop: 20,
                padding: 20,
                display: "flex",
              }}
            >
              <div className="col-xs-12" style={{ flexBasis: "100%" }}>
                <ResponsiveCirclePacking
                  {...this.properties}
                  data={{
                    name: "Listens",
                    color: "hsl(176, 70%, 50%)",
                    children: data,
                  }}
                  colors={{ scheme: "oranges" }}
                  colorBy="id"
                />
              </div>
              <div className="col-xs-12" style={{ flexBasis: "100%" }}>
                <ResponsiveCirclePacking
                  {...this.properties}
                  data={{
                    name: "Listens",
                    color: "hsl(176, 70%, 50%)",
                    children: data,
                  }}
                  colors={{ scheme: "oranges" }}
                  colorBy="id"
                  leavesOnly
                />
              </div>
            </div>
          )}
        </Loader>
      </Card>
    );
  }
}
