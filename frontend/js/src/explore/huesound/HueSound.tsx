/* eslint-disable jsx-a11y/anchor-is-valid */

import * as React from "react";
import { get, has } from "lodash";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { Link, useNavigate, useParams } from "react-router-dom";
import ColorWheel from "./components/ColorWheel";
import { convertColorReleaseToListen } from "./utils/utils";
import GlobalAppContext from "../../utils/GlobalAppContext";

import Loader from "../../components/Loader";
import ListenCard from "../../common/listens/ListenCard";
import Card from "../../components/Card";
import { COLOR_WHITE } from "../../utils/constants";
import { ToastMsg } from "../../notifications/Notifications";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

export default function HueSound() {
  const { colorURLParam } = useParams();
  const navigate = useNavigate();
  const { APIService } = React.useContext(GlobalAppContext);
  const { lookupReleaseFromColor } = APIService;
  const dispatch = useBrainzPlayerDispatch();
  const [loading, setLoading] = React.useState(false);
  const [colorReleases, setColorReleases] = React.useState<ColorReleaseItem[]>(
    []
  );
  const [selectedRelease, setSelectedRelease] = React.useState<
    ColorReleaseItem
  >();
  const [gridBackground, setGridBackground] = React.useState<string>(
    COLOR_WHITE
  );
  const navigateToColor = (rgbValue: string) => {
    const hexValue = tinycolor(rgbValue).toHex();
    navigate(`/explore/huesound/${hexValue}`);
  };

  const selectedReleaseTracks = selectedRelease?.recordings ?? [];
  React.useEffect(() => {
    if (!selectedReleaseTracks?.length) {
      return;
    }
    selectedReleaseTracks?.shift();
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: selectedReleaseTracks,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedReleaseTracks]);

  React.useEffect(() => {
    if (!tinycolor(colorURLParam).isValid()) {
      return;
    }
    setLoading(true);
    const hex = tinycolor(colorURLParam).toHex(); // returns hex value without leading '#'
    lookupReleaseFromColor(hex)
      .then((newColorReleases) => {
        const { releases } = newColorReleases.payload;
        const lighterColor = tinycolor(colorURLParam).lighten(40);
        setColorReleases(releases);
        setGridBackground(lighterColor.toRgbString());
      })
      .catch((err) => {
        toast.error(
          <ToastMsg
            title="Error"
            message={err.message ? err.message.toString() : err.toString()}
          />,
          { toastId: "error" }
        );
      })
      .finally(() => setLoading(false));
  }, [colorURLParam, lookupReleaseFromColor]);

  const selectRelease = React.useCallback((release: ColorReleaseItem) => {
    setSelectedRelease(release);
    window.postMessage(
      {
        brainzplayer_event: "play-listen",
        payload:
          release.recordings?.[0] ?? convertColorReleaseToListen(release),
      },
      window.location.origin
    );
  }, []);

  return (
    <div role="main">
      <Helmet>
        <title>Huesound</title>
      </Helmet>
      <div>
        <h1 className="text-center">
          Huesound<span className="beta">beta</span>
        </h1>
        <div className="row huesound-container">
          <div className="colour-picker-container">
            {colorReleases.length === 0 && (
              <h2 className="text-center">cover art music discovery</h2>
            )}
            <ColorWheel
              radius={175}
              padding={1}
              lineWidth={70}
              onColorSelected={navigateToColor}
              spacers={{
                colour: COLOR_WHITE,
                shadowColor: "grey",
                shadowBlur: 5,
              }}
              preset={!!colorURLParam} // You can set this bool depending on whether you have a pre-selected colour in state.
              presetColor={colorURLParam}
              animated
            />
            {!tinycolor(colorURLParam).isValid() && (
              <h2 className="text-center">
                Choose a color
                <br />
                on the wheel!
              </h2>
            )}
            {colorReleases.length > 0 && !selectedRelease && (
              <h2 className="text-center">
                Click an album cover to start playing!
              </h2>
            )}
          </div>
          <div
            className={`cover-art-grid ${
              !colorReleases?.length ? "invisible" : ""
            }`}
            style={{ backgroundColor: gridBackground }}
          >
            {colorReleases?.map((release, index) => {
              return (
                <button
                  // eslint-disable-next-line react/no-array-index-key
                  key={`${release.release_mbid}-${index}`}
                  onClick={(evt) => {
                    evt.preventDefault();
                    selectRelease(release);
                  }}
                  type="button"
                  className="cover-art-container"
                >
                  <img
                    src={`https://archive.org/download/mbid-${release.release_mbid}/mbid-${release.release_mbid}-${release.caa_id}_thumb250.jpg`}
                    alt={`Cover art for Release ${release.release_name}`}
                    height={150}
                  />
                </button>
              );
            })}
          </div>
        </div>

        {colorReleases.length > 0 && <Loader isLoading={loading} />}
        {selectedRelease && (
          <div className="row align-items-center">
            <div className="col-md-8" style={{ marginTop: "3em" }}>
              <Card style={{ display: "flex" }}>
                <img
                  className="img-rounded"
                  style={{ flex: 1 }}
                  src={`https://archive.org/download/mbid-${selectedRelease.release_mbid}/mbid-${selectedRelease.release_mbid}-${selectedRelease.caa_id}_thumb250.jpg`}
                  alt={`Cover art for Release ${selectedRelease.release_name}`}
                  width={200}
                  height={200}
                />
                <div style={{ flex: 3, padding: "0.5em 2em" }}>
                  <div className="h3">
                    <Link to={`/release/${selectedRelease.release_mbid}/`}>
                      {selectedRelease.release_name}
                    </Link>
                  </div>
                  <div className="h4">
                    {has(
                      selectedRelease,
                      "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                    ) ? (
                      <Link
                        to={`/artist/${get(
                          selectedRelease,
                          "recordings[0].track_metadata.additional_info.artist_mbids[0]"
                        )}/`}
                      >
                        {selectedRelease.artist_name}
                      </Link>
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
                        key={recording.track_metadata.track_name}
                        listen={recording}
                        showTimestamp={false}
                        showUsername={false}
                      />
                    );
                  }
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
