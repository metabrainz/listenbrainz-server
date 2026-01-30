import * as React from "react";

import { Link } from "react-router";
import { toast } from "react-toastify";
import { findKey, startCase } from "lodash";
import Select, { OptionProps, components } from "react-select";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faQuestionCircle,
} from "@fortawesome/free-solid-svg-icons";
import ReactTooltip from "react-tooltip";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { FlairEnum, Flair } from "../../utils/constants";
import type { FlairName } from "../../utils/constants";
import Username from "../../common/Username";
import queryClient from "../../utils/QueryClient";
import useUserFlairs from "../../utils/FlairLoader";
import useAutoSave from "../../hooks/useAutoSave";

function CustomOption(
  props: OptionProps<{ value: Flair; label: FlairName; username: string }>
) {
  const { label, data } = props;
  return (
    <components.Option {...props}>
      <div style={{ display: "flex", gap: "1em" }}>
        <span>{label}</span>
        <span style={{ marginLeft: "auto" }}>
          <FontAwesomeIcon icon={faArrowRight} />
        </span>
        <Username
          style={{ marginLeft: "auto" }}
          username={data.username}
          selectedFlair={data.value}
          hideLink
          elementType="a"
        />
      </div>
    </components.Option>
  );
}

export default function FlairsSettings() {
  /* Cast enum keys to array so we can map them to select options */
  const flairNames = Object.keys(FlairEnum) as FlairName[];

  const globalContext = React.useContext(GlobalAppContext);
  const { currentUser, APIService, flair: currentFlair } = globalContext;
  const { name } = currentUser;

  const [selectedFlair, setSelectedFlair] = React.useState<Flair>(
    currentFlair ?? FlairEnum.None
  );

  // NEW: Create ref to store current flair value
  const flairRef = React.useRef(selectedFlair);

  // NEW: Update ref whenever flair changes
  React.useEffect(() => {
    flairRef.current = selectedFlair;
  }, [selectedFlair]);
  // If this has a value it should tell us if the flair is active,
  // as calculated on the back-end
  const currentUnlockedFlair = useUserFlairs(name);
  // However we also hit the metabrainz nag-check endpoint to comfirm that
  // and get a number of days left
  const [flairUnlocked, setFlairUnlocked] = React.useState<boolean>(
    Boolean(currentUnlockedFlair)
  );
  const [unlockDaysLeft, setUnlockDaysLeft] = React.useState<number>(0);
  React.useEffect(() => {
    async function fetchNagStatus() {
      try {
        const response = await fetch(
          `https://metabrainz.org/donations/nag-check?editor=${name}`
        );
        const values = await response.text();
        // discard the "shouldNag" value
        const [_, daysLeft] = values.split(",");
        setUnlockDaysLeft(Math.max(Number(daysLeft), 0));
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("Could not fetch nag status:", error);
      }
    }
    fetchNagStatus();
  }, [name]);

  const submitFlairPreferences = React.useCallback(async () => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your preferences");
      return;
    }

    // Getting the current value from the ref
    const currentFlairValue = flairRef.current;

    await APIService.submitFlairPreferences(
      currentUser?.auth_token,
      // using refs instead
      currentFlairValue
    );

    globalContext.flair = flairRef.current;
    queryClient.invalidateQueries({ queryKey: ["flair"] });

    // not keeping selectedFlair in dependency since we are using ref now
  }, [APIService, currentUser?.auth_token, globalContext, queryClient]);

  // Auto-save hook  after 3 seconds
  const { triggerAutoSave } = useAutoSave({
    delay: 3000, // 3 sec wait
    onSave: submitFlairPreferences, // this funct will be called  when saving
    enabled: true,
  });

  // Tracking first render
  const isFirstRender = React.useRef(true);

  React.useEffect(() => {
    // Skip auto-save on first render - we only want to save when user makes changes
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    // Trigger auto-save whenever flair changes

    triggerAutoSave();
  }, [selectedFlair, triggerAutoSave]);

  return (
    <div className="mb-4 donation-flairs-settings">
      <div className="mb-4">
        <ReactTooltip id="flair-tooltip" place="bottom" multiline>
          Every $5 donation unlocks flairs for 1 month,
          <br />
          with larger donations extending the duration.
          <br />
          Donations stack up, adding more months
          <br />
          of unlocked flairs with each contribution.
        </ReactTooltip>
        <h3>Flair Settings</h3>
        <p>
          Unlock for a month or more by <Link to="/donate/">donating</Link>
          &nbsp;
          <FontAwesomeIcon
            icon={faQuestionCircle}
            data-tip
            data-for="flair-tooltip"
            size="sm"
          />
          .<br />
          Some flairs are only visible on hover.
        </p>
        {flairUnlocked ? (
          <div className="alert alert-success">
            Your flair is unlocked for another{" "}
            <b>{Math.round(unlockDaysLeft)} days</b>.
          </div>
        ) : (
          <div className="alert alert-warning">
            Flairs are currently locked; you can choose a flair below but it
            will not be shown on the website until your next donation.{" "}
            <FontAwesomeIcon
              icon={faQuestionCircle}
              data-tip
              data-for="flair-tooltip"
              size="sm"
            />
          </div>
        )}
        <p
          className="border-start border-info border-3 px-3 py-2 mb-3"
          style={{ backgroundColor: "rgba(248, 249, 250)", fontSize: "1.1em" }}
        >
          Changes are saved automatically.
        </p>
        <div
          className="flex flex-wrap"
          style={{ gap: "1em", alignItems: "center" }}
        >
          <div style={{ flexBasis: "300px", maxWidth: "400px" }}>
            <Select
              id="flairs"
              name="flairs"
              isMulti={false}
              value={{
                value: selectedFlair,
                label: startCase(
                  findKey(FlairEnum, (k) => k === selectedFlair)
                ) as FlairName,
                username: name,
              }}
              onChange={(newSelection) =>
                setSelectedFlair(newSelection?.value ?? FlairEnum.None)
              }
              options={flairNames.map((flairName) => ({
                value: FlairEnum[flairName],
                label: startCase(flairName) as FlairName,
                username: name,
              }))}
              components={{ Option: CustomOption }}
            />
          </div>
          <div
            className="alert alert-info"
            style={{ flex: "0 200px", textAlign: "center", margin: 0 }}
          >
            Preview:&nbsp;
            <Username
              username={name}
              selectedFlair={selectedFlair}
              hideLink
              elementType="a"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
