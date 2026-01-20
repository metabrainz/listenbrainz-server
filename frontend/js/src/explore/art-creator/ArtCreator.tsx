import * as React from "react";
import { useCallback, useState, useEffect } from "react";
import { debounce, isEqual } from "lodash";
import { saveAs } from "file-saver";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import NiceModal from "@ebay/nice-modal-react";
import { useSearchParams } from "react-router";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCircleXmark } from "@fortawesome/free-solid-svg-icons";
import localforage from "localforage";
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
import { getBaseUrl, getObjectForURLSearchParams } from "../../utils/utils";

const colorPresetStore = localforage.createInstance({
  name: "listenbrainz",
  driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE],
  storeName: "color-presets",
});

export enum TemplateNameEnum {
  designerTop5 = "designer-top-5",
  designerTop10 = "designer-top-10",
  designerTop10Alt = "designer-top-10-alt",
  lPsOnTheFloor = "lps-on-the-floor",
  gridStats = "grid-stats",
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

export interface ColorPreset {
  id: string;
  textColor: string;
  firstBgColor: string;
  secondBgColor: string;
}

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
  [TemplateNameEnum.designerTop10Alt]: {
    name: TemplateNameEnum.designerTop10Alt,
    displayName: "Designer top 10 (alt)",
    image: "/static/img/explore/stats-art/template-designer-top-10-alt.png",
    type: "text",
    defaultColors: ["#006D39", "#083B2B", "#111820"],
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

/* Layout options available for each grid dimension (number of rows/columns)
See GRID_TILE_DESIGNS in listenbrainz/art/cover_art_generator.py */
const coverArtGridOptions: CoverArtGridOptions[] = [
  { dimension: 1, layout: 0 },
  { dimension: 2, layout: 0 },
  { dimension: 3, layout: 0 },
  { dimension: 3, layout: 1 },
  { dimension: 3, layout: 2 },
  { dimension: 4, layout: 0 },
  { dimension: 4, layout: 1 },
  { dimension: 4, layout: 2 },
  { dimension: 4, layout: 3 },
  { dimension: 5, layout: 0 },
  { dimension: 5, layout: 1 },
];

const hardCodedPresets: ColorPreset[] = [
  {
    id: "1",
    textColor: "#e5cdc8",
    firstBgColor: "#6b4078",
    secondBgColor: "#33234c",
  },
  {
    id: "2",
    textColor: "#8a1515",
    firstBgColor: "#ff2f6e",
    secondBgColor: "#e8ff2c",
  },
  {
    id: "3",
    textColor: "#1f2170",
    firstBgColor: "#786aba",
    secondBgColor: "#ff0000",
  },
  {
    id: "4",
    textColor: "#dde2bb",
    firstBgColor: "#083023",
    secondBgColor: "#0fc26c",
  },
  {
    id: "5",
    textColor: "#006d39",
    firstBgColor: "#ffffff",
    secondBgColor: "#006d39",
  },
];

// enum FontNameEnum {
//   "Roboto",
//   "Integer",
//   "Sans Serif",
// }
// const fontOptions = Object.values(FontNameEnum).filter((v) => isNaN(Number(v)));

const DEFAULT_IMAGE_SIZE = 750;

const defaultStyleOnLoad = TemplateEnum[
  TemplateNameEnum.designerTop5
] as TextTemplateOption;

const defaultTimeRangeOnLoad: keyof typeof TimeRangeOptions = "this_month";

export default function ArtCreator() {
  const { currentUser, APIService } = React.useContext(GlobalAppContext);
  const [searchParams, setSearchParams] = useSearchParams();
  const updateSearchParam = useCallback(
    (param: string, value: string) => {
      setSearchParams((prevParams) => ({
        ...getObjectForURLSearchParams(prevParams),
        [param]: value,
      }));
    },
    [setSearchParams]
  );
  const userName = searchParams.get("username") ?? currentUser?.name;
  const setUserNameCallback = useCallback(
    (newUsername: string) => updateSearchParam("username", newUsername),
    [updateSearchParam]
  );
  const style: TemplateOption =
    TemplateEnum[searchParams.get("style") as TemplateNameEnum] ??
    defaultStyleOnLoad;

  const timeRange =
    searchParams.get("range")! in TimeRangeOptions
      ? (searchParams.get("range") as keyof typeof TimeRangeOptions)
      : defaultTimeRangeOnLoad;

  const [gridSize, setGridSize] = useState(4);
  const [gridLayout, setGridLayout] = useState(0);
  const [showCaption, setShowCaption] = useState(true);
  const [skipMissing, setSkipMissing] = useState(true);
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
  const [customPresets, setCustomPresets] = useState<ColorPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const previewSVGRef = React.useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!selectedPreset) {
      return;
    }
    const currentPreset = [...hardCodedPresets, ...customPresets].find(
      (preset) => preset.id === selectedPreset
    );
    if (currentPreset) {
      setTextColor(currentPreset.textColor);
      setFirstBgColor(currentPreset.firstBgColor);
      setSecondBgColor(currentPreset.secondBgColor);
    }
  }, [selectedPreset, customPresets]);

  useEffect(() => {
    const loadPresets = async () => {
      try {
        const [savedPresets, savedSelectedId] = await Promise.all([
          colorPresetStore.getItem<ColorPreset[]>("lb-art-custom-presets"),
          colorPresetStore.getItem<string>("lb-art-selected-preset"),
        ]);
        if (savedPresets) {
          setCustomPresets(savedPresets);
        }
        if (savedSelectedId) {
          const allCurrentPresets = [
            ...hardCodedPresets,
            ...(savedPresets || []),
          ];
          const currentPreset = allCurrentPresets.find(
            (preset) => preset.id === savedSelectedId
          );
          if (currentPreset) {
            setSelectedPreset(currentPreset.id);
          }
        }
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Failed to load the preset"
            message={error?.message ?? String(error)}
          />,
          { toastId: "load-preset-error" }
        );
      }
    };

    loadPresets();
  }, []);

  const saveCurrentPreset = async () => {
    if (!textColor || !firstBgColor || !secondBgColor) {
      toast.error("Please select all the colors before saving");
      return;
    }

    const isDuplicate = [...hardCodedPresets, ...customPresets].some(
      (preset: ColorPreset) =>
        preset.textColor.toLowerCase() === textColor.toLowerCase() &&
        preset.firstBgColor.toLowerCase() === firstBgColor.toLowerCase() &&
        preset.secondBgColor.toLowerCase() === secondBgColor.toLowerCase()
    );

    if (isDuplicate) {
      toast.error("This preset already exists");
      return;
    }

    const newPreset: ColorPreset = {
      id: Date.now().toString(),
      textColor,
      firstBgColor,
      secondBgColor,
    };

    try {
      const updatedPresets = [...customPresets, newPreset];
      await colorPresetStore.setItem("lb-art-custom-presets", updatedPresets);
      await colorPresetStore.setItem("lb-art-selected-preset", newPreset.id);
      setCustomPresets(updatedPresets);
      setSelectedPreset(newPreset.id);
      toast.success(<ToastMsg title="Success" message="Preset saved" />, {
        toastId: "save-preset-success",
      });
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Failed to save the preset"
          message={error?.message ?? String(error)}
        />,
        { toastId: "save-preset-error" }
      );
    }
  };

  const deletePreset = async (presetId: string) => {
    try {
      const updatedPresets = customPresets.filter(
        (preset) => preset.id !== presetId
      );
      await colorPresetStore.setItem("lb-art-custom-presets", updatedPresets);
      setCustomPresets(updatedPresets);

      if (selectedPreset === presetId) {
        setSelectedPreset(hardCodedPresets[0].id);
        await colorPresetStore.setItem(
          "lb-art-selected-preset",
          hardCodedPresets[0].id
        );
      }
      toast.success(<ToastMsg title="Success" message="Preset deleted" />, {
        toastId: "delete-preset-success",
      });
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Failed to delete Preset"
          message={error?.message ?? String(error)}
        />,
        { toastId: "delete-preset-error" }
      );
    }
  };

  const applyPreset = async (presetId: string) => {
    try {
      setSelectedPreset(presetId);
      await colorPresetStore.setItem("lb-art-selected-preset", presetId);
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not apply preset"
          message={error?.message ?? String(error)}
        />,
        { toastId: "apply-preset-error" }
      );
    }
  };

  const updateStyleButtonCallback = useCallback(
    (name: TemplateNameEnum) => {
      const selectedStyle: TemplateOption = TemplateEnum[name];
      updateSearchParam("style", selectedStyle.name);
      if (selectedStyle.type === "grid") {
        setGridLayout((selectedStyle as GridTemplateOption).defaultGridLayout);
        setGridSize((selectedStyle as GridTemplateOption).defaultGridSize);
      }
    },
    [updateSearchParam]
  );

  React.useEffect(() => {
    // On page load, validate URL params and set defaults if invalid
    const validStyleOrDefault: TemplateNameEnum =
      TemplateEnum[searchParams.get("style") as TemplateNameEnum]?.name ??
      defaultStyleOnLoad.name;
    updateStyleButtonCallback(validStyleOrDefault);
    if (!(searchParams.get("range")! in TimeRangeOptions)) {
      updateSearchParam("range", defaultTimeRangeOnLoad);
    }
  }, []);

  const updateStyleCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) =>
      updateStyleButtonCallback(event.target.value as TemplateNameEnum),
    [updateStyleButtonCallback]
  );

  const updateTimeRangeCallback = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      updateSearchParam("range", event.target.value);
    },
    [updateSearchParam]
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
          ? `${getBaseUrl()}/syndication-feed/user/${encodeURIComponent(
              userName
            )}/stats/art/grid?dimension=${gridSize}&layout=${gridLayout}&range=${timeRange}`
          : `${getBaseUrl()}/syndication-feed/user/${encodeURIComponent(
              userName
            )}/stats/art/custom?custom_name=${style.name}&range=${timeRange}`,
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
        gridLayoutArg: number,
        showCaptionArg: boolean,
        skipMissingArg: boolean
      ) => {
        if (styleArg.type === "grid") {
          let newPreviewUrl = `${
            APIService.APIBaseURI
          }/art/grid-stats/${encodeURIComponent(
            userNameArg
          )}/${timeRangeArg}/${gridSizeArg}/${gridLayoutArg}/${DEFAULT_IMAGE_SIZE}`;
          const queryParams = new URLSearchParams();
          if (!showCaptionArg) {
            queryParams.set("caption", "false");
          }
          if (!skipMissingArg) {
            queryParams.set("skip-missing", "false");
          }
          if (queryParams.size) {
            newPreviewUrl += `?${queryParams.toString()}`;
          }
          setPreviewUrl(newPreviewUrl);
        } else {
          setPreviewUrl(
            `${APIService.APIBaseURI}/art/${styleArg.name}/${encodeURIComponent(
              userNameArg
            )}/${timeRangeArg}/${DEFAULT_IMAGE_SIZE}`
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
    debouncedSetPreviewUrl(
      style,
      userName,
      timeRange,
      gridSize,
      gridLayout,
      showCaption,
      skipMissing
    );
  }, [
    userName,
    style,
    timeRange,
    gridSize,
    gridLayout,
    showCaption,
    skipMissing,
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
            showCaption={showCaption}
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
                <label className="input-group-text" htmlFor="user-name">
                  Username
                </label>
                <UserSearch
                  initialValue={userName}
                  onSelectUser={setUserNameCallback}
                  placeholder="Search for a user…"
                />
              </div>
              <div className="input-group">
                <label className="input-group-text" htmlFor="style">
                  Template
                </label>
                <select
                  id="style"
                  className="form-select"
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
                <label className="input-group-text" htmlFor="time-range">
                  Time range
                </label>
                <select
                  id="time-range"
                  className="form-select"
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
                  <label className="form-check-label">
                    <input
                      className="form-check-input me-2"
                      type="checkbox"
                      checked={showCaption}
                      onChange={(evt) => setShowCaption(evt.target.checked)}
                    />{" "}
                    Show caption
                  </label>
                  <label className="form-check-label">
                    <input
                      className="form-check-input me-2"
                      type="checkbox"
                      checked={skipMissing}
                      onChange={(evt) => setSkipMissing(evt.target.checked)}
                    />{" "}
                    Skip missing covers
                  </label>
                  <small>Choose a grid layout:</small>
                  <div className="cover-art-grid">
                    {coverArtGridOptions.map((option) => {
                      return (
                        <label className="cover-art-option">
                          <input
                            type="radio"
                            name="artwork"
                            value={`artwork-${option.dimension}-${option.layout}`}
                            key={`artwork-${option.dimension}-${option.layout}`}
                            className="cover-art-radio"
                            checked={
                              isEqual(option.dimension, gridSize) &&
                              isEqual(option.layout, gridLayout)
                            }
                            onChange={() => {
                              setGridSize(option.dimension);
                              setGridLayout(option.layout);
                            }}
                          />
                          <img
                            height={80}
                            width={80}
                            src={`/static/img/playlist-cover-art/cover-art_${option.dimension}-${option.layout}.svg`}
                            alt={`Cover art option ${option.dimension}-${option.layout}`}
                            className="cover-art-image"
                          />
                        </label>
                      );
                    })}
                  </div>
                </>
              )}
              {style.type === "text" && (
                <>
                  <div>
                    <label className="form-label" htmlFor="color-presets">
                      Color presets:
                    </label>
                    <div className="color-presets-panel" id="color-presets">
                      {hardCodedPresets.map((preset) => (
                        <div
                          key={preset.id}
                          className={`color-preset-wrapper ${
                            selectedPreset === preset.id
                              ? "preset-selected"
                              : ""
                          }`}
                        >
                          <ColorPicker
                            firstColor={preset.firstBgColor}
                            secondColor={preset.secondBgColor}
                            onClick={() => applyPreset(preset.id)}
                          />
                        </div>
                      ))}

                      {customPresets.map((preset) => (
                        <div
                          key={preset.id}
                          className={`color-preset-wrapper ${
                            selectedPreset === preset.id
                              ? "preset-selected"
                              : ""
                          }`}
                        >
                          <ColorPicker
                            firstColor={preset.firstBgColor}
                            secondColor={preset.secondBgColor}
                            onClick={() => applyPreset(preset.id)}
                          />
                          <button
                            type="button"
                            className="delete-preset-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              deletePreset(preset.id);
                            }}
                            aria-label="Delete preset"
                            title="Delete this preset"
                          >
                            <FontAwesomeIcon icon={faCircleXmark} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="form-label" htmlFor="text-color-input">
                      Text color:
                    </label>
                    <div className="input-group">
                      <input
                        id="text-color-input"
                        type="color"
                        className="form-control form-control-color"
                        onChange={updateTextColorCallback}
                        placeholder="#321529"
                        value={textColor}
                      />
                      <input
                        className="form-control"
                        type="text"
                        placeholder="#321529"
                        value={textColor}
                        readOnly
                      />
                    </div>
                  </div>
                  <div>
                    <label className="form-label" htmlFor="bg-color">
                      Background colors:
                    </label>
                    <div className="input-group">
                      <input
                        id="bg-color"
                        type="color"
                        className="form-control form-control-color"
                        onChange={updateFirstBgColorCallback}
                        value={firstBgColor}
                      />
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Select a color…"
                        readOnly
                        value={firstBgColor}
                      />
                    </div>
                  </div>

                  <div className="input-group">
                    <input
                      id="bg-color-2"
                      type="color"
                      className="form-control form-control-color"
                      onChange={updateSecondBgColorCallback}
                      value={secondBgColor}
                    />
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Select a color…"
                      readOnly
                      value={secondBgColor}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn-info w-100"
                    onClick={saveCurrentPreset}
                  >
                    Save Preset
                  </button>
                </>
              )}
              {/* <div className="flex-center input-group">
                <label className="form-label" htmlFor="bg-upload">Background image:</label>
                <input className="form-control" type="text" />
                <button type="button" className="btn btn-secondary btn-sm">
                  <FontAwesomeIcon icon={faCloudArrowUp} />
                </button>
              </div> */}

              {/* <div>
                <label className="form-label" htmlFor="genres">
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
                className="form-label" htmlFor="font-select">Font:</label>
                <select
                  id="font-select"
                  className="form-select"
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
