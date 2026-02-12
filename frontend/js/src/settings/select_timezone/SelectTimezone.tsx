import * as React from "react";

import { useLoaderData } from "react-router";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import useAutoSave from "../../hooks/useAutoSave";

type SelectTimezoneLoaderData = {
  pg_timezones: Array<string[]>;
  user_timezone: string;
};

export default function SelectTimezone() {
  const data = useLoaderData() as SelectTimezoneLoaderData;
  // user_timezone stores value returned by route loader
  const { pg_timezones, user_timezone } = data;

  const globalContext = React.useContext(GlobalAppContext);
  const { APIService, currentUser } = globalContext;
  // currentTimezone stores immediate local React state
  const [currentTimezone, setCurrentTimezone] = React.useState(user_timezone);

  React.useEffect(() => {
    setCurrentTimezone(user_timezone);
  }, [user_timezone]);

  const submitTimezone = React.useCallback(
    async (newTimezone: string) => {
      if (!currentUser?.auth_token) {
        toast.error("You must be logged in to update your timezone");
        return;
      }

      await APIService.resetUserTimezone(currentUser.auth_token, newTimezone);
    },
    [APIService, currentUser?.auth_token]
  );

  const { triggerAutoSave } = useAutoSave<string>({
    delay: 3000,
    onSave: submitTimezone,
  });

  const handleSave = (zone: string) => {
    setCurrentTimezone(zone);
    triggerAutoSave(zone);
  };

  return (
    <>
      <Helmet>
        <title>Select your timezone</title>
      </Helmet>
      <h3>Select your timezone</h3>
      <p>
        Your timezone is{" "}
        <span style={{ fontWeight: "bold" }}>{currentTimezone}.</span>
      </p>

      <p>
        Setting your timezone allows us to generate local timestamps and better
        statistics for your listens. It also influences when your daily
        playlists and recommendations are generated.
      </p>

      <p className="border-start bg-light border-info border-3 px-3 py-2 mb-3 fs-4">
        Changes are saved automatically.
      </p>
      <div>
        <label>
          Select your local timezone:{" "}
          <select
            className="form-select"
            value={currentTimezone}
            onChange={(e) => handleSave(e.target.value)}
          >
            <option value="default" disabled>
              Choose an option
            </option>
            {pg_timezones.map((zone: string[]) => {
              return (
                <option key={zone[0]} value={zone[0]}>
                  {zone[0]} ({zone[1]})
                </option>
              );
            })}
          </select>
        </label>
      </div>
    </>
  );
}
