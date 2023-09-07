import {
  faCircleQuestion,
  faCloudArrowUp,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as Sentry from "@sentry/react";
import { Integrations } from "@sentry/tracing";
import * as React from "react";
import { useCallback, useState } from "react";
import { debounce, isNaN } from "lodash";
import { saveAs } from "file-saver";
import { toast } from "react-toastify";
import NiceModal from "@ebay/nice-modal-react";
import { createRoot } from "react-dom/client";
import withAlertNotifications from "../../notifications/AlertNotificationsHOC";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";
import ColorPicker from "./components/ColorPicker";
import Gallery from "./components/Gallery";
import IconTray from "./components/IconTray";
import Preview from "./components/Preview";
import ToggleOption from "./components/ToggleOption";
import { svgToBlob, toPng } from "./utils";
import { ToastMsg } from "../../notifications/Notifications";
import UserSearch from "../../playlists/UserSearch";

export enum TemplateNameEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
  gridStatsSpecial = "grid-stats-special",
}

export interface TemplateOption {
  name: TemplateNameEnum;
  displayName: string;
  image: string;
  type: "text" | "image" | "grid";
}
export interface TextTemplateOption extends TemplateOption {
  type: "text";
  defaultColors: readonly string[];
}
export interface GridTemplateOption extends TemplateOption {
  type: "grid";
  defaultGridSize: number;
  defaultGridLayout: number;
}
/* How many layouts are available fro each grid dimension (number of rows/columns)
See GRID_TILE_DESIGNS in listenbrainz/art/cover_art_generator.py */
const layoutsPerGridDimensionArr = [undefined, undefined, 1, 3, 4, 2];

/* Fancy TypeScript to get a typed enum of object literals representing the options */
export type TemplateEnumType = {
  [key in TemplateNameEnum]:
    | TemplateOption
    | TextTemplateOption
    | GridTemplateOption;
};
export const TemplateEnum: TemplateEnumType = {
  [TemplateNameEnum.designerTop5]: {
    name: TemplateNameEnum.designerTop5,
    displayName: "Designer top 5",
    image: "/static/img/explore/stats-art/template-designer-top-5.png",
    type: "text",
    defaultColors: ["#321529", "#9b3361", "#a76798"],
  },
  [TemplateNameEnum.designerTop10]: {
    name: TemplateNameEnum.designerTop10,
    displayName: "Designer top 10",
    image: "/static/img/explore/stats-art/template-designer-top-10.png",
    type: "text",
    defaultColors: ["#FAFF5B", "#00A2CC", "#FF29A5"],
  },
  [TemplateNameEnum.lPsOnTheFloor]: {
    name: TemplateNameEnum.lPsOnTheFloor,
    displayName: "LPs on the floor",
    image: "/static/img/explore/stats-art/template-lps-on-the-floor.png",
    type: "image",
  },
  [TemplateNameEnum.gridStats]: {
    name: TemplateNameEnum.gridStats,
    displayName: "Album grid",
    image: "/static/img/explore/stats-art/template-grid-stats.png",
    type: "grid",
    defaultGridSize: 4,
    defaultGridLayout: 0,
  },
  [TemplateNameEnum.gridStatsSpecial]: {
    name: TemplateNameEnum.gridStatsSpecial,
    displayName: "Album grid alt",
    image: "/static/img/explore/stats-art/template-grid-stats-2.png",
    type: "grid",
    defaultGridSize: 5,
    defaultGridLayout: 1,
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

// enum FontNameEnum {
//   "Roboto",
//   "Integer",
//   "Sans Serif",
// }

const DEFAULT_IMAGE_SIZE = 750;

// const fontOptions = Object.values(FontNameEnum).filter((v) => isNaN(Number(v)));

const defaultStyleOnLoad = TemplateEnum["designer-top-5"] as TextTemplateOption;

function ArtCreator() {
  const { currentUser } = React.useContext(GlobalAppContext);
  // Add images for the gallery, don't compose them on the fly
  const [userName, setUserName] = useState(currentUser?.name);
  const [style, setStyle] = useState<TemplateOption>(defaultStyleOnLoad);
  const [timeRange, setTimeRange] = useState<keyof typeof TimeRangeOptions>(
    "this_month"
  );
  const [gridSize, setGridSize] = useState(4);
  const [gridLayout, setGridLayout] = useState(0);
  const [previewUrl, setPreviewUrl] = useState("");
  // const [font, setFont] = useState<keyof typeof FontNameEnum>("Roboto");
  const [textColor, setTextColor] = useState<string>(
    defaultStyleOnLoad.defaultColors[0]
  );
  const [firstBgColor, setFirstBgColor] = useState<string>(
    defaultStyleOnLoad.defaultColors[1]
  );
  const [secondBgColor, setSecondBgColor] = useState<string>(
    defaultStyleOnLoad.defaultColors[2]
  );
  const previewSVGRef = React.useRef<SVGSVGElement>(null);

  const updateStyleButtonCallback = useCallback(
    (name: TemplateNameEnum) => {
      const selectedStyle = TemplateEnum[name];
      setStyle(selectedStyle);
      if (selectedStyle.type === "grid") {
        setGridLayout((selectedStyle as GridTemplateOption).defaultGridLayout);
        setGridSize((selectedStyle as GridTemplateOption).defaultGridSize);
      } else if (selectedStyle.type === "text") {
        setTextColor((selectedStyle as TextTemplateOption).defaultColors[0]);
        setFirstBgColor((selectedStyle as TextTemplateOption).defaultColors[1]);
        setSecondBgColor(
          (selectedStyle as TextTemplateOption).defaultColors[2]
        );
      }
    },
    [setStyle]
  );
  const updateStyleCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      setStyle(TemplateEnum[event.target.value as TemplateNameEnum]),
    [setStyle]
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

  const onClickDownload = useCallback(async () => {
    if (!previewSVGRef?.current) {
      return;
    }
    const { current: svgElement } = previewSVGRef;
    const { outerHTML } = svgElement;
    try {
      const png = await toPng(
        DEFAULT_IMAGE_SIZE,
        DEFAULT_IMAGE_SIZE,
        outerHTML
      );
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
      const { outerHTML } = svgElement;
      const svgBlob = await svgToBlob(
        DEFAULT_IMAGE_SIZE,
        DEFAULT_IMAGE_SIZE,
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
      (
        styleArg: TemplateOption,
        userNameArg: string,
        timeRangeArg: keyof typeof TimeRangeOptions,
        gridSizeArg: number,
        gridLayoutArg: number
      ) => {
        if (styleArg.type === "grid") {
          setPreviewUrl(
            `https://api.listenbrainz.org/1/art/grid-stats/${userNameArg}/${timeRangeArg}/${gridSizeArg}/${gridLayoutArg}/${DEFAULT_IMAGE_SIZE}`
          );
        } else {
          setPreviewUrl(
            `https://api.listenbrainz.org/1/art/${styleArg.name}/${userNameArg}/${timeRangeArg}/${DEFAULT_IMAGE_SIZE}`
          );
        }
      },
      1000,
      { leading: false }
    );
  }, [setPreviewUrl]);
  React.useEffect(() => {
    if (!userName) {
      return;
    }
    debouncedSetPreviewUrl(style, userName, timeRange, gridSize, gridLayout);
  }, [
    userName,
    style,
    timeRange,
    gridSize,
    gridLayout,
    debouncedSetPreviewUrl,
  ]);

  return (
    <div id="stats-art-creator">
      <div className="artwork-container">
        <Gallery
          currentStyle={style}
          options={templatesArray}
          onStyleSelect={updateStyleButtonCallback}
        />
        <hr />
        <IconTray
          previewUrl={previewUrl}
          onClickDownload={onClickDownload}
          onClickCopy={onClickCopyImage}
          onClickCopyCode={onClickCopyCode}
        />
        <Preview
          url={previewUrl}
          styles={{
            textColor,
            bgColor1: firstBgColor,
            bgColor2: secondBgColor,
          }}
          ref={previewSVGRef}
          size={DEFAULT_IMAGE_SIZE}
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
              <UserSearch
                initialValue={userName}
                onSelectUser={setUserName}
                placeholder="Search for a user…"
              />
            </div>
            <div className="input-group">
              <label className="input-group-addon" htmlFor="style">
                Template
              </label>
              <select
                id="style"
                className="form-control"
                value={style.name}
                onChange={updateStyleCallback}
              >
                {templatesArray.map((opt) => (
                  <option key={opt.name} value={opt.name}>
                    {opt.displayName}
                  </option>
                ))}
              </select>
            </div>
            <div className="input-group">
              <label className="input-group-addon" htmlFor="time-range">
                Time range
              </label>
              <select
                id="time-range"
                className="form-control"
                value={timeRange}
                onChange={updateTimeRangeCallback}
              >
                {Object.entries(TimeRangeOptions).map((opt) => (
                  <option key={opt[0]} value={opt[0]}>
                    {opt[1]}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="advanced-settings-container">
          <div className="sidenav-content-grid">
            <h4>Advanced</h4>
            {style.type === "grid" && (
              <>
                <small>
                  You can customize the grid size and select one of our advanced
                  layouts
                </small>
                <div className="input-group">
                  <label className="input-group-addon" htmlFor="albums-per-row">
                    Albums per row
                  </label>
                  <input
                    id="albums-per-row"
                    className="form-control"
                    type="number"
                    min={2}
                    max={5}
                    value={gridSize}
                    onChange={(event) => {
                      setGridSize(event.target.valueAsNumber);
                      setGridLayout(0);
                    }}
                  />
                </div>
                <div className="input-group">
                  <label className="input-group-addon" htmlFor="grid-layout">
                    Grid layout
                  </label>
                  <select
                    id="grid-layout"
                    className="form-control"
                    value={gridLayout + 1}
                    onChange={(event) => {
                      setGridLayout(Number(event.target.value) - 1);
                    }}
                  >
                    {[...Array(layoutsPerGridDimensionArr[gridSize])].map(
                      (val, index) => {
                        return (
                          <option key={`option-${index + 1}`} value={index + 1}>
                            Option {index + 1}
                          </option>
                        );
                      }
                    )}
                  </select>
                </div>
              </>
            )}
            {style.type === "text" && (
              <>
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
              </>
            )}
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
              <select
                id="font-select"
                className="form-control"
                value={font}
                onChange={updateFontCallback}
              >
                {fontOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
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
