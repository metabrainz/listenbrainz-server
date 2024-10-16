import * as React from "react";

import { Helmet } from "react-helmet";
import { toast } from "react-toastify";
import GlobalAppContext from "../../utils/GlobalAppContext";

const flairOptions = [
  { label: "Default", value: "default", className: "default" },
  { label: "Fire", value: "fire", className: "fire" },
  { label: "Water", value: "water", className: "water" },
  { label: "Air", value: "air", className: "air" },
  { label: "Disabled", value: "disabled", className: "disabled" },
];

export default function FlairSettings() {
  const globalContext = React.useContext(GlobalAppContext);
  const { currentUser, APIService } = globalContext;
  let currentFlair = globalContext.flair;

  const [selectedFlairs, setSelectedFlairs] = React.useState<FlairPreferences>(
    currentFlair || "default"
  );

  const submitFlairPreferences = async () => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your preferences");
      return;
    }
    const response = await APIService.submitFlairPreferences(
      currentUser?.auth_token,
      selectedFlairs
    );
    toast.success("Flair preferences updated successfully");

    currentFlair = selectedFlairs;
  };

  const userName = currentUser?.name;

  return (
    <>
      <Helmet>
        <title>Flairs settings</title>
      </Helmet>
      <h2 className="page-title">Flairs settings</h2>
      <p>
        Choose which flairs do you want to use for donation in ListenBrainz.
      </p>

      <div className="mb-15 donation-flairs-settings">
        <div className="form-group">
          <h3>Flairs</h3>
          <p>
            Choose which flair do you want to use for donation in ListenBrainz.
          </p>
          <div className="radio-group-horizontal" id="flairs">
            {flairOptions.map((option, index) => (
              <div key={option.value} className="radio-item">
                <label
                  htmlFor={`flairs-${index}`}
                  className="radio-label-above"
                >
                  {userName}
                </label>
                <input
                  id={`flairs-${index}`}
                  type="radio"
                  name="flairs"
                  value={option.value}
                  checked={selectedFlairs === option.value}
                  onChange={(e) =>
                    setSelectedFlairs(e.target.value as FlairPreferences)
                  }
                />
                <span className="radio-description">{option.label}</span>
              </div>
            ))}
          </div>
          <button
            onClick={submitFlairPreferences}
            className="btn btn-lg btn-info"
            type="button"
          >
            Submit
          </button>
        </div>
      </div>
    </>
  );
}
