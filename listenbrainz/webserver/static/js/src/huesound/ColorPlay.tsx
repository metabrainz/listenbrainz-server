/* eslint-disable jsx-a11y/anchor-is-valid */

import * as ReactDOM from "react-dom";
import * as React from "react";
import { get, has } from "lodash";
import tinycolor from "tinycolor2";
import ColorWheel from "./ColorWheel";
import defaultColors from "./utils/defaultColors";
import ErrorBoundary from "../ErrorBoundary";
import GlobalAppContext, { GlobalAppContextT } from "../GlobalAppContext";
import {
  WithAlertNotificationsInjectedProps,
  withAlertNotifications,
} from "../AlertNotificationsHOC";

import APIServiceClass from "../APIService";
import BrainzPlayer from "../BrainzPlayer";
import Loader from "../components/Loader";
import { convertColorReleaseToListen, getPageProps } from "../utils";
import ListenCard from "../listens/ListenCard";
import Card from "../components/Card";

export type ColorPlayProps = {
  user: ListenBrainzUser;
} & WithAlertNotificationsInjectedProps;

export type ColorPlayState = {
  direction: BrainzPlayDirection;
  colorReleases: Array<ColorReleaseItem>;
  loading: boolean;
  selectedRelease?: ColorReleaseItem;
  selectedColorString?: string;
  gridBackground: string;
};

export default class ColorPlay extends React.Component<
  ColorPlayProps,
  ColorPlayState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: ColorPlayProps) {
    super(props);
    this.state = {
      colorReleases: [],
      loading: false,
      direction: "down",
      gridBackground: "#FFFFFF",
    };
  }

  onColorChanged = async (rgbString: string) => {
    const { newAlert } = this.props;
    const { APIService } = this.context;
    const hex = tinycolor(rgbString).toHex(); // returns hex value without leading '#'
    try {
      const colorReleases: ColorReleasesResponse = await APIService.lookupReleaseFromColor(
        hex
      );
      const { releases } = colorReleases.payload;
      const lighterColor = tinycolor(rgbString).lighten(40);
      this.setState({
        colorReleases: releases,
        selectedColorString: rgbString,
        gridBackground: lighterColor.toRgbString(),
      });
    } catch (err) {
      newAlert(
        "danger",
        "",
        err.message ? err.message.toString() : err.toString()
      );
    }
  };

  selectRelease = (
    release: ColorReleaseItem,
    event: React.MouseEvent<HTMLImageElement>
  ) => {
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
    const {
      direction,
      loading,
      colorReleases,
      selectedRelease,
      selectedColorString,
      gridBackground,
    } = this.state;
    const { currentUser } = this.context;

    const selectedReleaseTracks = selectedRelease?.recordings ?? [];
    return (
      <div role="main">
        <div>
          <h3 className="text-center">Huesound Color Play (alpha version)</h3>
          <div className="row vertical-align">
            <div
              className={`col-md-4 ${
                selectedColorString ? "" : "col-md-offset-4"
              }`}
              style={{ transition: "all 1s" }}
            >
              <h1 className="text-center">Pick a Color</h1>
              <ColorWheel
                radius={175}
                padding={1}
                lineWidth={70}
                onColorSelected={this.onColorChanged}
                spacers={{
                  colour: "#FFFFFF",
                  shadowColor: "grey",
                  shadowBlur: 5,
                }}
                colours={defaultColors}
                preset={false} // You can set this bool depending on whether you have a pre-selected colour in state.
                presetColor={selectedColorString}
                animated
              />
              {colorReleases.length === 0 && (
                <h1 className="text-center">Click on the wheel</h1>
              )}
              {colorReleases.length > 0 && !selectedRelease && (
                <h3 className="text-center">
                  Now click on an album cover to listen to that album
                </h3>
              )}
            </div>
            {colorReleases && colorReleases.length > 0 && (
              <>
                <div
                  className="col-md-8 coverArtGrid"
                  style={{ backgroundColor: gridBackground }}
                >
                  {colorReleases.map((release, index) => {
                    return (
                      // eslint-disable-next-line react/no-array-index-key
                      <div key={index}>
                        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events,jsx-a11y/no-noninteractive-element-interactions */}
                        <img
                          src={`https://coverartarchive.org/release/${release.release_mbid}/${release.caa_id}-250.jpg`}
                          alt={`Cover art for Release ${release.release_name}`}
                          width={142}
                          height={142}
                          onClick={this.selectRelease.bind(this, release)}
                        />
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          {colorReleases.length > 0 && <Loader isLoading={loading} />}
          {selectedRelease && (
            <div className="row align-items-center">
              <div className="col-md-8" style={{ marginTop: "3em" }}>
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
              <div className="col-md-4 sticky-top">
                <BrainzPlayer
                  direction={direction}
                  newAlert={newAlert}
                  listens={selectedReleaseTracks}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalReactProps } = getPageProps();
  const { api_url, current_user, spotify, youtube } = globalReactProps;
  const { user } = reactProps;

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
        <ColorPlayWithAlertNotifications user={user} />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
