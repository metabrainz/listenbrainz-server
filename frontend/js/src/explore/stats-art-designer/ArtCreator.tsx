import {
  faCircleQuestion,
  faCloudArrowUp,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import * as React from "react";
import { useCallback, useState } from "react";
import { debounce } from "lodash";
import { saveAs } from "file-saver";
import { toast } from "react-toastify";
import NiceModal from "@ebay/nice-modal-react";
import { createRoot } from "react-dom/client";
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
import { svgToBlob, toPng } from "./utils";
import { ToastMsg } from "../../notifications/Notifications";

export enum TemplateNameEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
}

export interface TemplateOption {
  name: TemplateNameEnum;
  displayName: string;
  image: string;
  type: "text" | "image";
}

/* Fancy TypeScript to get a typed enum of object literals representing the options */
export type TemplateEnumType = {
  [key in TemplateNameEnum]: TemplateOption;
};
export const TemplateEnum: TemplateEnumType = {
  [TemplateNameEnum.designerTop5]: {
    name: TemplateNameEnum.designerTop5,
    displayName: "Designer top 5",
    image: "/static/img/explore/stats-art/template-designer-top-5.png",
    type: "text",
  },
  [TemplateNameEnum.designerTop10]: {
    name: TemplateNameEnum.designerTop10,
    displayName: "Designer top 10",
    image: "/static/img/explore/stats-art/template-designer-top-10.png",
    type: "text",
  },
  [TemplateNameEnum.lPsOnTheFloor]: {
    name: TemplateNameEnum.lPsOnTheFloor,
    displayName: "LPs on the floor",
    image: "/static/img/explore/stats-art/template-lps-on-the-floor.png",
    type: "image",
  },
  [TemplateNameEnum.gridStats]: {
    name: TemplateNameEnum.gridStats,
    displayName: "Stats grid",
    image: "/static/img/explore/stats-art/template-grid-stats.png",
    type: "image",
  },
} as const;

const templatesArray = Object.values(TemplateEnum);

enum TimeRangeOptions {
  "this_week" = "This week",
  "week" = "Last week",
  "this_month" = "This month",
  "month" = "Last month",
  "quarter" = "Last quarter",
  "half_yearly" = "Last half year",
  "this_year" = "This year",
  "year" = "Last year",
  "all_time" = "All time",
}

function ArtCreator() {
  const { currentUser } = React.useContext(GlobalAppContext);
  // Add images for the gallery, don't compose them on the fly
  const [userName, setUserName] = useState(currentUser?.name);
  const [style, setStyle] = useState<TemplateOption>(
    TemplateEnum["designer-top-5"]
  );
  const [timeRange, setTimeRange] = useState<keyof typeof TimeRangeOptions>(
    "week"
  );
  const [gridSize, setGridSize] = useState(4);
  const [gridStyle, setGridStyle] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  const [font, setFont] = useState("");
  const [textColor, setTextColor] = useState<string>("#321529");
  const [firstBgColor, setFirstBgColor] = useState<string>("");
  const [secondBgColor, setSecondBgColor] = useState<string>("");
  const [genres, setGenres] = useState("");
  const [usersToggle, setUsersToggle] = useState(false);
  const [dateToggle, setDateToggle] = useState(false);
  const [rangeToggle, setRangeToggle] = useState(false);
  const [totalToggle, setTotalToggle] = useState(false);
  const [genresToggle, setGenresToggle] = useState(false);
  const [vaToggle, setVaToggle] = useState(false);
  const previewSVGRef = React.useRef<SVGSVGElement>(null);

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

  const fontOpts = [
    ["Roboto", "Roboto"],
    ["Integer", "Integer"],
    ["Sans Serif", "Sans Serif"],
  ];

  const updateStyleButtonCallback = useCallback(
    (name: TemplateNameEnum) => {
      setStyle(TemplateEnum[name]);
    },
    [setStyle]
  );
  const updateStyleCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setStyle(TemplateEnum[event.target.value as TemplateNameEnum]),
    [setStyle]
  );

  const updateUserNameCallback = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) =>
      setUserName(event.target.value),
    [setUserName]
  );

  const updateTimeRangeCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setTimeRange(event.target.value as keyof typeof TimeRangeOptions),
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

  const onClickDownload = useCallback(async () => {
    if (!previewSVGRef?.current) {
      return;
    }
    const { current: svgElement } = previewSVGRef;
    const { width, height } = svgElement.getBBox();
    const { outerHTML } = svgElement;
    try {
      const png = await toPng(width, height, outerHTML);
      if (!png) {
        return;
      }
      saveAs(
        png,
        `ListenBrainz-stats-${userName}-${TimeRangeOptions[timeRange]}.png`
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not save as an image"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "download-svg-error" }
      );
    }
  }, [previewSVGRef, userName, timeRange]);

  const onClickCopyImage = useCallback(async () => {
    if (!previewSVGRef?.current) {
      return;
    }
    try {
      const { current: svgElement } = previewSVGRef;
      const { width, height } = svgElement.getBBox();
      const { outerHTML } = svgElement;
      const svgBlob = await svgToBlob(
        width,
        height,
        outerHTML,
        "image/svg+xml"
      );
      console.debug("svgBlob", svgBlob);
      const data = [new ClipboardItem({ [svgBlob.type]: svgBlob })];
      await navigator.clipboard.write(data);
      toast.success("Copied image");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy SVG image"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "copy-svg-error" }
      );
    }
  }, [previewSVGRef]);

  const onClickCopyCode = useCallback(async () => {
    if (!previewSVGRef?.current) {
      return;
    }
    try {
      const { current: svgElement } = previewSVGRef;
      const { outerHTML } = svgElement;
      await navigator.clipboard.writeText(outerHTML);
      toast.success("Copied image source");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy SVG image source"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "copy-svg-error" }
      );
    }
  }, [previewSVGRef]);
  /* We want the username input to update as fast as the user types,
  but we don't want to update the preview URL on each keystroke so we debounce */
  const debouncedSetPreviewUrl = React.useMemo(() => {
    return debounce(
      (styleArg, userNameArg, timeRangeArg, gridSizeArg, gridStyleArg) => {
        if (styleArg === TemplateNameEnum.gridStats) {
          setPreviewUrl(
            `https://api.listenbrainz.org/1/art/${styleArg}/${userNameArg}/${timeRangeArg}/${gridSizeArg}/${gridStyleArg}/750`
          );
        } else {
          setPreviewUrl(
            `https://api.listenbrainz.org/1/art/${styleArg}/${userNameArg}/${timeRangeArg}/750`
          );
        }
      },
      1000,
      { leading: false }
    );
  }, [setPreviewUrl]);
  React.useEffect(() => {
    debouncedSetPreviewUrl(style, userName, timeRange, gridSize, gridStyle);
  }, [userName, style, timeRange, gridSize, gridStyle, debouncedSetPreviewUrl]);

  return (
    <div id="stats-art-creator">
      <div className="artwork-container">
        <Gallery
          currentStyle={style}
          options={templatesArray}
          onStyleSelect={updateStyleButtonCallback}
        />
        <hr />
        <Preview
          url={previewUrl}
          styles={{
            textColor,
            bgColor1: firstBgColor,
            bgColor2: secondBgColor,
          }}
          ref={previewSVGRef}
        />
        <IconTray
          previewUrl={previewUrl}
          onClickDownload={onClickDownload}
          onClickCopy={onClickCopyImage}
          onClickCopyCode={onClickCopyCode}
        />
      </div>
      <div className="sidebar settings-navbar">
        <div className="basic-settings-container">
          <div className="sidenav-content-grid">
            <h4>Settings</h4>
            <div className="input-group">
              <label className="input-group-addon" htmlFor="user-name">
                Username
              </label>
              <input
                id="user-name"
                type="text"
                value={userName}
                onChange={updateUserNameCallback}
                placeholder="user name.."
                className="form-control"
              />
            </div>
            <div className="input-group">
              <label className="input-group-addon" htmlFor="style">
                Template
              </label>
              <DropdownList
                id="style"
                opts={styleOpts}
                value={style}
                onChange={updateStyleCallback}
              />
            </div>
            {/* <div className="input-group">
              <label className="input-group-addon" htmlFor="top-x">
                Top
              </label>
              <input
                id="top-x"
                className="form-control"
                type="number"
                defaultValue="5"
              />
            </div> */}
            <div className="input-group">
              <label className="input-group-addon" htmlFor="time-range">
                Time range
              </label>
              <DropdownList
                id="time-range"
                opts={Object.entries(TimeRangeOptions)}
                value={timeRange}
                onChange={updateTimeRangeCallback}
              />
            </div>
            <div>
              <label htmlFor="color-presets">Color presets:</label>
              <div className="color-picker-panel" id="color-presets">
                <ColorPicker
                  firstColor="#6b4078"
                  secondColor="#33234c"
                  onClick={() => {
                    setTextColor("#e5cdc8");
                    setFirstBgColor("#6b4078");
                    setSecondBgColor("#33234c");
                  }}
                />
                <ColorPicker
                  firstColor="#ff2f6e"
                  secondColor="#e8ff2c"
                  onClick={() => {
                    setTextColor("#8a1515");
                    setFirstBgColor("#ff2f6e");
                    setSecondBgColor("#e8ff2c");
                  }}
                />
                <ColorPicker
                  firstColor="#786aba"
                  secondColor="#ff0000"
                  onClick={() => {
                    setTextColor("#1f2170");
                    setFirstBgColor("#786aba");
                    setSecondBgColor("#ff0000");
                  }}
                />
                <ColorPicker
                  firstColor="#083023"
                  secondColor="#0fc26c"
                  onClick={() => {
                    setTextColor("#dde2bb");
                    setFirstBgColor("#083023");
                    setSecondBgColor("#0fc26c");
                  }}
                />
                <ColorPicker
                  firstColor="#ffffff"
                  secondColor="#006d39"
                  onClick={() => {
                    setTextColor("#006d39");
                    setFirstBgColor("#ffffff");
                    setSecondBgColor("#006d39");
                  }}
                />
              </div>
            </div>
          </div>
        </div>
        <div className="advanced-settings-container">
          <div className="sidenav-content-grid">
            <h4>Advanced</h4>
            <div>
              <label htmlFor="text-color-input">Text color:</label>
              <div className="input-group">
                <span className="input-group-btn">
                  <input
                    id="text-color-input"
                    type="color"
                    className="btn btn-transparent form-control"
                    onChange={updateTextColorCallback}
                    placeholder="#321529"
                    value={textColor}
                  />
                </span>
                <input
                  className="form-control"
                  type="text"
                  placeholder="#321529"
                  value={textColor}
                  disabled
                />
              </div>
            </div>
            <div>
              <label htmlFor="bg-color">Background colors:</label>
              <div className="input-group">
                <span className="input-group-btn">
                  <input
                    id="bg-color"
                    type="color"
                    className="btn btn-transparent form-control"
                    onChange={updateFirstBgColorCallback}
                    value={firstBgColor}
                  />
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Select a color…"
                  disabled
                  readOnly
                  value={firstBgColor}
                />
              </div>
            </div>

            <div className="input-group">
              <span className="input-group-btn">
                <input
                  id="bg-color-2"
                  type="color"
                  className="btn btn-transparent form-control"
                  onChange={updateSecondBgColorCallback}
                  value={secondBgColor}
                />
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Select a color…"
                disabled
                readOnly
                value={secondBgColor}
              />
            </div>
            {/* <div className="flex-center input-group">
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
            </div> */}

            {/* <div>
              <label htmlFor="genres">
                Genres: <FontAwesomeIcon icon={faCircleQuestion} />
              </label>
              <input
                id="genres"
                type="text"
                className="form-control"
                onChange={updateGenresCallback}
              />
            </div> */}
            {/* <div>
              <ToggleOption onClick={userToggler} buttonName="Users" />
              <ToggleOption onClick={dateToggler} buttonName="Date" />
              <ToggleOption onClick={rangeToggler} buttonName="Range" />
              <ToggleOption onClick={totalToggler} buttonName="Total" />
              <ToggleOption onClick={genresToggler} buttonName="Genres" />
            </div> */}
            {/* <div>
              <label htmlFor="font-select">Font:</label>
              <DropdownList
                id="font-select"
                opts={fontOpts}
                value={style}
                onChange={updateFontCallback}
              />
            </div> */}
            {/* <div>
              <ToggleOption onClick={vaToggler} buttonName="Ignore VA" />
            </div> */}
          </div>
        </div>
        {/* <div className="generate-button-container">
          <button
            type="button"
            className="btn btn-block btn-info text-uppercase"
          >
            Generate
          </button>
        </div> */}
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

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <ArtCreatorPageWithAlertNotifications />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
