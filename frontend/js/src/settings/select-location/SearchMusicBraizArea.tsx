import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { throttle } from "lodash";
import React, {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "react-toastify";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";

type SearchAreaMusicBrainzProps = {
  onSelectArea: (selectedArea: MusicBrainzArea) => void;
  defaultValue?: string;
};

export default function SearchAreaMusicBrainz({
  onSelectArea,
  defaultValue,
}: SearchAreaMusicBrainzProps) {
  const { APIService } = useContext(GlobalAppContext);
  const { lookupMBArea } = APIService;
  const inputRef = useRef<HTMLInputElement>(null);
  const [inputValue, setInputValue] = useState(defaultValue ?? "");
  const [searchResults, setSearchResults] = useState<Array<MusicBrainzArea>>(
    []
  );

  useEffect(() => {
    // autoFocus property on the input element does not work
    // We need to wait for the modal animated transition to finish
    // and trigger the focus manually.
    inputRef?.current?.focus();
  }, []);

  const handleError = useCallback(
    (error: string | Error, title?: string): void => {
      if (!error) {
        return;
      }
      toast.error(
        <ToastMsg
          title={title || "Error"}
          message={typeof error === "object" ? error.message : error}
        />,
        { toastId: "search-error" }
      );
    },
    []
  );

  const throttledSearchArea = useMemo(
    () =>
      throttle(
        async (searchString: string) => {
          if (searchString.length === 0) return;
          try {
            const response = await lookupMBArea(searchString);
            setSearchResults(response.areas);
          } catch (error) {
            handleError(error);
          }
        },
        800,
        { leading: false, trailing: true }
      ),
    [handleError, setSearchResults]
  );

  const reset = () => {
    setInputValue("");
    setSearchResults([]);
  };

  useEffect(() => {
    throttledSearchArea(inputValue);
  }, [inputValue]);

  const onAreaSelectHandler = (area: MusicBrainzArea) => {
    // Hide the dropdown box
    reset();
    setInputValue(area.name);
    onSelectArea(area);
  };

  return (
    <div>
      <div className="input-group track-search">
        <input
          type="text"
          value={inputValue}
          className="form-control"
          id="area-mbid"
          name="area-mbid"
          onChange={(event) => {
            event.preventDefault();
            setInputValue(event.target.value);
          }}
          placeholder="Search Area"
          required
          ref={inputRef}
        />
        <span className="input-group-btn">
          <button className="btn btn-default" type="button" onClick={reset}>
            <FontAwesomeIcon icon={faTimesCircle} />
          </button>
        </span>
        <div />
        {Boolean(searchResults?.length) && (
          <div className="track-search-dropdown">
            {searchResults.map((area) => {
              return (
                <button
                  key={area.id}
                  type="button"
                  onClick={() => onAreaSelectHandler(area)}
                >
                  {`${area.name}`}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
