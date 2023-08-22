import {
  faCircleQuestion,
  faCloudArrowUp,
  faPaintBrush,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import * as React from "react";
import { useCallback, useState } from "react";
import * as ReactDOM from "react-dom";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import ColorPicker from "./components/ColorPicker";
import DropdownList from "./components/DropdownList";
import Gallery from "./components/Gallery";
import IconTray from "./components/IconTray";
import Preview from "./components/Preview";
import ToggleOption from "./components/ToggleOption";

enum StyleEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
}

function ArtCreator() {
  const { currentUser } = React.useContext(GlobalAppContext);
  // Add images for the gallery, don't compose them on the fly
  const [userName, setUserName] = useState(currentUser?.name);
  const [style, setStyle] = useState(StyleEnum.designerTop5);
  const [timeRange, setTimeRange] = useState("week");
  const [gridSize, setGridSize] = useState(4);
  const [gridStyle, setGridStyle] = useState(0);
  const [font, setFont] = useState("");
  const [textColor, setTextColor] = useState("");
  const [firstBgColor, setFirstBgColor] = useState("");
  const [secondBgColor, setSecondBgColor] = useState("");
  const [genres, setGenres] = useState("");
  const [usersToggle, setUsersToggle] = useState(false);
  const [dateToggle, setDateToggle] = useState(false);
  const [rangeToggle, setRangeToggle] = useState(false);
  const [totalToggle, setTotalToggle] = useState(false);
  const [genresToggle, setGenresToggle] = useState(false);
  const [vaToggle, setVaToggle] = useState(false);

  const userToggler = useCallback(() => {
    if (usersToggle) {
      setUsersToggle(false);
    } else {
      setUsersToggle(true);
    }
  }, [usersToggle]);

  const dateToggler = useCallback(() => {
    if (dateToggle) {
      setDateToggle(false);
    } else {
      setDateToggle(true);
    }
  }, [dateToggle]);

  const rangeToggler = useCallback(() => {
    if (rangeToggle) {
      setRangeToggle(false);
    } else {
      setRangeToggle(true);
    }
  }, [rangeToggle]);

  const totalToggler = useCallback(() => {
    if (totalToggle) {
      setTotalToggle(false);
    } else {
      setTotalToggle(true);
    }
  }, [totalToggle]);

  const genresToggler = useCallback(() => {
    if (genresToggle) {
      setGenresToggle(false);
    } else {
      setGenresToggle(true);
    }
  }, [genresToggle]);

  const vaToggler = useCallback(() => {
    if (vaToggle) {
      setVaToggle(false);
    } else {
      setVaToggle(true);
    }
  }, [vaToggle]);

  const styleOpts = [
    [StyleEnum.designerTop5, "Designer top 5"],
    [StyleEnum.designerTop10, "Designer top 10"],
    [StyleEnum.lPsOnTheFloor, "LPs on the floor"],
    [StyleEnum.gridStats, "Stats grid"],
  ];

  const galleryOpts = [
    {
      name: StyleEnum.designerTop5,
      url: "https://api.listenbrainz.org/1/art/designer-top-5/rob/week/750",
    },
    {
      name: StyleEnum.designerTop10,
      url: "https://api.listenbrainz.org/1/art/designer-top-10/rob/week/750",
    },
    {
      name: StyleEnum.lPsOnTheFloor,
      url: "https://api.listenbrainz.org/1/art/lps-on-the-floor/rob/week/750",
    },
    {
      name: StyleEnum.gridStats,
      url: "https://api.listenbrainz.org/1/art/grid-stats/rob/month/5/0/750",
    },
  ];

  const timeRangeOpts = [
    ["week", "Last week"],
    ["month", "Last month"],
    ["quarter", "last quarter"],
    ["half_yearly", "Last half year"],
    ["year", "Last year"],
    ["all_time", "All time"],
    ["this_week", "This week"],
    ["this_month", "This month"],
    ["this_year", "This year"],
  ];
  const fontOpts = [
    ["Roboto", "Roboto"],
    ["Integer", "Integer"],
    ["Sans Serif", "Sans Serif"],
  ];

  const updateStyleButtonCallback = useCallback(
    (name: string) => {
      setStyle(name as StyleEnum);
    },
    [setStyle]
  );
  const updateStyleCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setStyle(event.target.value as StyleEnum),
    [setStyle]
  );

  const updateUserNameCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setUserName(event.target.value),
    [setUserName]
  );

  const updateTimeRangeCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setTimeRange(event.target.value),
    [setTimeRange]
  );

  const updateTextColorCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setTextColor(event.target.value),
    [setTextColor]
  );
  const updateFirstBgColorCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setFirstBgColor(event.target.value),
    [setFirstBgColor]
  );
  const updateSecondBgColorCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setSecondBgColor(event.target.value),
    [setSecondBgColor]
  );
  const updateGenresCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setGenres(event.target.value),
    [setGenres]
  );

  const updateGridSizeCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setGridSize(Number(event.target.value)),
    [setGridSize]
  );

  const updateGridStyleCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setGridStyle(Number(event.target.value)),
    [setGridStyle]
  );

  const updateFontCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      setFont(event.target.value);
    },
    [setFont]
  );

  let previewUrl = "";
  if (style === "grid-stats") {
    previewUrl = `https://api.listenbrainz.org/1/art/${style}/${userName}/${timeRange}/${gridSize}/${gridStyle}/750`;
  } else {
    previewUrl = `https://api.listenbrainz.org/1/art/${style}/${userName}/${timeRange}/750`;
  }

  return (
    <div id="stats-art-creator">
      <div className="artwork-container">
        <Gallery
          currentStyle={style}
          galleryOpts={galleryOpts}
          onStyleSelect={updateStyleButtonCallback}
        />
        <hr />
        <Preview url={previewUrl} />
        <IconTray previewUrl={previewUrl} />
      </div>
      <div className="sidebar settings-navbar">
        <div className="basic-settings-container">
          <div className="sidenav-content-grid">
            <h4>Settings</h4>
            <input
              type="text"
              value={userName}
              onChange={updateUserNameCallback}
              placeholder="user name.."
              className="form-control"
            />
            <DropdownList
              opts={styleOpts}
              value={style}
              onChange={updateStyleCallback}
            />
            <div className="flex-center">
              <div>top:</div>
              <input className="form-control" type="text" placeholder="5" />
            </div>
            <DropdownList
              opts={timeRangeOpts}
              value={timeRange}
              onChange={updateTimeRangeCallback}
            />
            <div className="color-picker-panel">
              <ColorPicker firstColor="#6b4078" secondColor="#33234c" />
              <ColorPicker firstColor="#ff2f6e" secondColor="#e8ff2c" />
              <ColorPicker firstColor="#786aba" secondColor="#faff5b" />
              <ColorPicker firstColor="#083023" secondColor="#006d39" />
              <ColorPicker firstColor="#ffffff" secondColor="#006d39" />
            </div>
          </div>
        </div>
        <div className="advanced-settings-container">
          <div className="sidenav-content-grid">
            <h4>Advanced</h4>
            <div>
              <label htmlFor="text-color">Text color:</label>
              <div className="color-container input-group">
                <input
                  id="text-color"
                  className="form-control"
                  type="text"
                  onChange={updateTextColorCallback}
                  placeholder="#321529"
                />
                <span className="input-group-btn">
                  <button type="button" className="btn btn-default btn-sm">
                    <FontAwesomeIcon icon={faPaintBrush} />
                  </button>
                </span>
              </div>
            </div>
            <div>
              <label htmlFor="bg-color">Background color:</label>
              <div className="color-container input-group">
                <input
                  id="bg-color"
                  type="text"
                  className="form-control"
                  onChange={updateFirstBgColorCallback}
                  placeholder="#321529"
                />
                <span className="input-group-btn">
                  <button type="button" className="btn btn-default btn-sm">
                    <FontAwesomeIcon icon={faPaintBrush} />
                  </button>
                </span>
              </div>
            </div>

            <div className="color-container input-group">
              <input
                type="text"
                className="form-control"
                onChange={updateSecondBgColorCallback}
                placeholder="#321529"
              />
              <span className="input-group-btn">
                <button type="button" className="btn btn-default btn-sm">
                  <FontAwesomeIcon icon={faPaintBrush} />
                </button>
              </span>
            </div>
            <div className="flex-center color-container input-group">
              <label htmlFor="bg-upload">Background image:</label>
              <div className="input-group">
                <input className="form-control" type="text" disabled />
                <div className="input-group-btn">
                  <button type="button" className="btn btn-default btn-sm">
                    <FontAwesomeIcon icon={faCloudArrowUp} />
                  </button>
                  <input id="bg-upload" type="file" className="hidden" />
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="genres">
                Genres: <FontAwesomeIcon icon={faCircleQuestion} />
              </label>
              <input
                id="genres"
                type="text"
                className="form-control"
                onChange={updateGenresCallback}
              />
            </div>
            <div>
              <ToggleOption onClick={userToggler} buttonName="Users" />
              <ToggleOption onClick={dateToggler} buttonName="Date" />
              <ToggleOption onClick={rangeToggler} buttonName="Range" />
              <ToggleOption onClick={totalToggler} buttonName="Total" />
              <ToggleOption onClick={genresToggler} buttonName="Genres" />
            </div>
            <div>
              <label htmlFor="font-select">Font:</label>
              <DropdownList
                id="font-select"
                opts={fontOpts}
                value={style}
                onChange={updateFontCallback}
              />
            </div>
            <div>
              <ToggleOption onClick={vaToggler} buttonName="Ignore VA" />
            </div>
          </div>
        </div>
        <div className="generate-button-container">
          <button
            type="button"
            className="btn btn-block btn-info text-uppercase"
          >
            Generate
          </button>
        </div>
      </div>
    </div>
  );
}

export default ArtCreator;

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, globalAppContext, sentryProps } = getPageProps();
  const { sentry_dsn, sentry_traces_sample_rate } = sentryProps;

  if (sentry_dsn) {
    Sentry.init({
      dsn: sentry_dsn,
      integrations: [new Integrations.BrowserTracing()],
      tracesSampleRate: sentry_traces_sample_rate,
    });
  }
  const ArtCreatorPageWithAlertNotifications = withAlertNotifications(
    ArtCreator
  );

  ReactDOM.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <ArtCreatorPageWithAlertNotifications />
      </GlobalAppContext.Provider>
    </ErrorBoundary>,
    domContainer
  );
});
