import * as React from "react";
import { useCallback, useState } from "react";
import { debounce } from "lodash";
import { saveAs } from "file-saver";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import NiceModal from "@ebay/nice-modal-react";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ColorPicker from "./components/ColorPicker";
import Gallery from "./components/Gallery";
import IconTray from "./components/IconTray";
import Preview from "./components/Preview";
import { svgToBlob, toPng } from "./utils";
import { ToastMsg } from "../../notifications/Notifications";
import UserSearch from "../../common/UserSearch";
import Sidebar from "../../components/Sidebar";
import SyndicationFeedModal from "../../components/SyndicationFeedModal";
import { getBaseUrl } from "../../utils/utils";

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

export default function ArtCreator() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
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
      if (!navigator.clipboard) {
        throw new Error("No clipboard functionality detected for this browser");
      }
      if ("write" in navigator.clipboard) {
        const svgBlobPromise = svgToBlob(
          DEFAULT_IMAGE_SIZE,
          DEFAULT_IMAGE_SIZE,
          outerHTML,
          "image/png"
        );
        let data: ClipboardItems;
        if ("ClipboardItem" in window) {
          data = [new ClipboardItem({ "image/png": await svgBlobPromise })];
        } else {
          // For browers with no support for ClipboardItem
          throw new Error(
            "ClipboardItem is not available. User may be on FireFox with asyncClipboard.clipboardItem disabled"
          );
        }
        // Safari browsers require that we await our promise directly in the ClipboardItem call
        // rather than await the clipboard() function call
        // https://stackoverflow.com/questions/66312944/javascript-clipboard-api-write-does-not-work-in-safari*/
        navigator.clipboard
          .write(data)
          .then(() => {
            toast.success("Copied image to clipboard");
          })
          .catch((err) => {
            throw err;
          });
        return;
      }
      if ("writeText" in navigator.clipboard) {
        // We can't copy the image directly, but we can fall back to writing the SVG source string to the clipboard
        await (navigator.clipboard as Clipboard).writeText(outerHTML);
        toast.success("Copied image SVG to clipboard");
        return;
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy image to clipboard"
          message={
            <>
              This feature might not be supported in your browser or may be
              behind an experimental setting
              <br />
              {typeof error === "object" ? error.message : error.toString()}
            </>
          }
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
      toast.success("Copied SVG image source to clipboard");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy SVG image source to clipboard"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "copy-svg-error" }
      );
    }
  }, [previewSVGRef]);

  const onClickCopyURL = useCallback(async () => {
    if (!previewUrl) {
      return;
    }
    try {
      await navigator.clipboard.writeText(previewUrl);
      toast.success("Copied link to clipboard");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy link to clipboard"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "copy-link-error" }
      );
    }
  }, [previewUrl]);

  const onClickCopyAlt = useCallback(async () => {
    if (!previewSVGRef?.current) {
      return;
    }
    try {
      const { current: svgElement } = previewSVGRef;
      let altText = "";
      altText += svgElement.getElementsByTagName("title")[0].innerHTML;
      altText += svgElement.getElementsByTagName("desc")[0].innerHTML;
      await navigator.clipboard.writeText(altText);
      toast.success("Copied alt text to clipboard");
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not copy alt-text to clipboard"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "copy-alt-error" }
      );
    }
  }, [previewSVGRef]);

  const onClickCopyFeedUrl = useCallback(() => {
    NiceModal.show(SyndicationFeedModal, {
      feedTitle: `Stats Art`,
      options: [],
      baseUrl:
        style.type === "grid"
          ? `${getBaseUrl()}/syndication-feed/user/${userName}/stats/art/grid?dimension=${gridSize}&layout=${gridLayout}&range=${timeRange}`
          : `${getBaseUrl()}/syndication-feed/user/${userName}/stats/art/custom?custom_name=${
              style.name
            }&range=${timeRange}`,
    });
  }, [userName, style, gridSize, gridLayout, timeRange]);

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
            `${APIService.APIBaseURI}/art/grid-stats/${userNameArg}/${timeRangeArg}/${gridSizeArg}/${gridLayoutArg}/${DEFAULT_IMAGE_SIZE}`
          );
        } else {
          setPreviewUrl(
            `${APIService.APIBaseURI}/art/${styleArg.name}/${userNameArg}/${timeRangeArg}/${DEFAULT_IMAGE_SIZE}`
          );
        }
      },
      1000,
      { leading: false }
    );
  }, [setPreviewUrl, APIService.APIBaseURI]);
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
    <div role="main">
      <Helmet>
        <title>Art Creator</title>
      </Helmet>
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
            onClickCopyURL={onClickCopyURL}
            onClickCopyAlt={onClickCopyAlt}
            onClickCopyFeedUrl={onClickCopyFeedUrl}
          />
          <Preview
            key={previewUrl}
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
        <Sidebar className="settings-navbar">
          <div className="sidebar-header">
            <p>Art Creator</p>
            <p>Visualize and share images of your listening stats.</p>
            <p>
              Select your username, a date range and a template to a dynamic
              image that you can save, copy and share easily with your friends.
              Check out the #ListenbrainzMonday tag on your social platform of
              choice!
            </p>
          </div>
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
                    You can customize the grid size and select one of our
                    advanced layouts
                  </small>
                  <div className="input-group">
                    <label
                      className="input-group-addon"
                      htmlFor="albums-per-row"
                    >
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
                            <option
                              key={`option-${index + 1}`}
                              value={index + 1}
                            >
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
        </Sidebar>
      </div>
    </div>
  );
}
