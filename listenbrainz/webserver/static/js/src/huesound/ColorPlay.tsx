/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import { ColorResult, SwatchesPicker } from "react-color";
import { get, has } from "lodash";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import Loader from "../components/Loader";
import {
  convertColorReleaseToListen,
  getPageProps,
  lighterColor,
} from "../utils";
import ListenCard from "../listens/ListenCard";
import Card from "../components/Card";

export type ColorPlayProps = {
  user: ListenBrainzUser;
  totalCount: number;
  profileUrl?: string;
} & WithAlertNotificationsInjectedProps;

export type ColorPlayState = {
  direction: BrainzPlayDirection;
  colorReleases: Array<ColorReleaseItem>;
  page: number;
  maxPage: number;
  loading: boolean;
  selectedRelease?: ColorReleaseItem;
};

export default class ColorPlay extends React.Component<
  ColorPlayProps,
  ColorPlayState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;
  private APIService!: APIServiceClass;

  private DEFAULT_TRACKS_PER_PAGE = 25;

  constructor(props: ColorPlayProps) {
    super(props);
    const { totalCount } = this.props;
    this.state = {
      maxPage: Math.ceil(totalCount / this.DEFAULT_TRACKS_PER_PAGE),
      colorReleases: [],
      page: 1,
      loading: false,
      direction: "down",
    };
  }

  async componentDidMount(): Promise<void> {
    // Listen to browser previous/next events and load page accordingly
    window.addEventListener("popstate", this.handleURLChange);
    this.handleURLChange();
    const { APIService } = this.context;
    this.APIService = APIService;
  }

  componentWillUnmount() {
    window.removeEventListener("popstate", this.handleURLChange);
  }

  // pagination functions
  handleURLChange = async (): Promise<void> => {
    const { page, maxPage } = this.state;
    const url = new URL(window.location.href);

    if (url.searchParams.get("page")) {
      let newPage = Number(url.searchParams.get("page"));
      if (newPage === page) {
        // page didn't change
        return;
      }
      newPage = Math.max(newPage, 1);
      newPage = Math.min(newPage, maxPage);
    } else if (page !== 1) {
      // occurs on back + forward history
    }
  };

  handleClickOlder = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
  };

  handleClickNewer = async (event?: React.MouseEvent) => {
    if (event) {
      event.preventDefault();
    }
  };

  onColorChanged = async (color: ColorResult) => {
    let { hex } = color;
    hex = hex.substring(1); // remove # from the start of the color
    const colorReleases: ColorReleasesResponse = await this.APIService.lookupReleaseFromColor(
      hex
    );
    const { releases } = colorReleases.payload;
    this.setState({
      colorReleases: releases,
    });
  };

  selectRelease = (
    release: ColorReleaseItem,
    event: React.MouseEvent<HTMLImageElement>
  ) => {
    const tint = lighterColor(release.color);
    document.body.style.backgroundColor = `rgb(${tint[0]},${tint[1]},${tint[2]})`;
    this.setState({ selectedRelease: release }, () => {
      window.postMessage(
        {
          brainzplayer_event: "play-listen",
          payload:
            release.recordings?.[0] ?? convertColorReleaseToListen(release),
        },
        window.location.origin
      );
    });
  };

  render() {
    const { user, newAlert } = this.props;
    const { direction, loading, colorReleases, selectedRelease } = this.state;
    const { currentUser } = this.context;

    const selectedReleaseTracks = selectedRelease?.recordings ?? [];
    return (
      <div role="main">
        <div className="row">
          <div className="col-md-8">
            <h3>Huesound Color Play</h3>

            {colorReleases.length === 0 && (
              <>
                <div className="lead text-center">No Tracks found</div>

                {user.name === currentUser.name && <>Click on the wheel</>}
              </>
            )}

            {colorReleases && (
              <div className="coverArtGrid">
                {colorReleases.map((release, index) => {
                  return (
                    // eslint-disable-next-line react/no-array-index-key
                    <div key={index}>
                      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events,jsx-a11y/no-noninteractive-element-interactions */}
                      <img
                        src={`https://coverartarchive.org/release/${release.release_mbid}/${release.caa_id}-250.jpg`}
                        alt={`Cover art for Release ${release.release_name}`}
                        width={125}
                        height={125}
                        onClick={this.selectRelease.bind(this, release)}
                      />
                    </div>
                  );
                })}
              </div>
            )}
            {colorReleases.length > 0 && <Loader isLoading={loading} />}

            {selectedRelease && (
              <div style={{ marginTop: "3em" }}>
                <Card style={{ display: "flex" }}>
                  <img
                    className="img-rounded"
                    style={{ flex: 1 }}
                    src={`https://coverartarchive.org/release/${selectedRelease.release_mbid}/${selectedRelease.caa_id}-250.jpg`}
                    alt={`Cover art for Release ${selectedRelease.release_name}`}
                    width={200}
                    height={200}
                  />
                  <div style={{ flex: 3, padding: "0.5em 2em" }}>
                    <div className="h3">
                      <a
                        href={`https://musicbrainz.org/release/${selectedRelease.release_mbid}`}
                      >
                        {selectedRelease.release_name}
                      </a>
                    </div>
                    <div className="h4">
                      {has(
                        selectedRelease,
                        "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                      ) ? (
                        <a
                          href={`https://musicbrainz.org/artist/${get(
                            selectedRelease,
                            "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                          )}`}
                        >
                          {selectedRelease.artist_name}
                        </a>
                      ) : (
                        selectedRelease.artist_name
                      )}
                    </div>
                  </div>
                </Card>
                <div style={{ padding: "2em" }}>
                  {selectedRelease.recordings?.map(
                    (recording: BaseListenFormat) => {
                      return (
                        <ListenCard
                          listen={recording}
                          currentFeedback={0}
                          showTimestamp={false}
                          showUsername={false}
                          newAlert={newAlert}
                        />
                      );
                    }
                  )}
                </div>
              </div>
            )}
          </div>
          <div
            className="col-md-4"
            // @ts-ignore
            // eslint-disable-next-line no-dupe-keys
            style={{ position: "-webkit-sticky", position: "sticky", top: 20 }}
          >
            <div style={{ marginBottom: 10 }}>
              <SwatchesPicker onChangeComplete={this.onColorChanged} />
            </div>
            <BrainzPlayer
              direction={direction}
              newAlert={newAlert}
              listens={selectedReleaseTracks}
            />
          </div>
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user, total_count, profile_url } = reactProps;

  const apiService = new APIServiceClass(
    api_url || `${window.location.origin}/1`
  );

  const ColorPlayWithAlertNotifications = withAlertNotifications(ColorPlay);

  const globalProps: GlobalAppContextT = {
    APIService: apiService,
    currentUser: current_user,
    spotifyAuth: spotify,
    youtubeAuth: youtube,
  };

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalProps}>
        <ColorPlayWithAlertNotifications
          user={user}
          totalCount={total_count}
          profileUrl={profile_url}
        />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
