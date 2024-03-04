import React, {
  FormEvent,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import SearchAreaMusicBrainz from "./SearchMusicBraizArea";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { ToastMsg } from "../../notifications/Notifications";

interface SelectAreaProps {
  area: MusicBrainzArea | null;
}

type SelectAreaLoaderData = SelectAreaProps;

export function SelectArea({ area: initialArea }: SelectAreaProps) {
  const { APIService, currentUser } = useContext(GlobalAppContext);
  const [currentArea, setCurrentArea] = useState<MusicBrainzArea | null>(
    initialArea
  );
  let currentSelectedArea: MusicBrainzArea | null = initialArea;
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

  const submitArea = async (event: FormEvent) => {
    event.preventDefault();
    try {
      if (currentSelectedArea == null) {
        toast.error(<ToastMsg title="Please select an area" message="" />);
        return;
      }
      await APIService.submitArea(
        currentUser.auth_token as string,
        currentSelectedArea
      );
      setCurrentArea(currentSelectedArea);
      toast.success(
        <ToastMsg title="Your area has been successfully saved" message="" />
      );
    } catch (error) {
      handleError(error);
    }
  };
  return (
    <>
      <h3>Select Area</h3>
      <p>
        Your current area setting is{" "}
        <span style={{ fontWeight: "bold" }}>
          {currentArea?.name ?? "[none]"}.
        </span>
        <br />
        Choosing your area lets us tell you about upcoming events in your area.
        You can be as broad (Country) as you like or as specific (Town) as you
        like. <b>This information will be public.</b>
      </p>

      <div>
        <form>
          <br />
          <br />
          <SearchAreaMusicBrainz
            onSelectArea={(newArea) => {
              currentSelectedArea = newArea;
            }}
          />
          <br />
          <br />
          <button
            type="submit"
            className="btn btn-info btn-lg"
            onClick={submitArea}
          >
            Save Area
          </button>
        </form>
      </div>
    </>
  );
}

export function SelectAreaWrapper() {
  const data = useLoaderData() as SelectAreaLoaderData;
  return <SelectArea area={data.area} />;
}

export const SelectAreaLoader = async () => {
  const response = await fetch("/settings/select_area/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return data;
};

export default SelectArea;
