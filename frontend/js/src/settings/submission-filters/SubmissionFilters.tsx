import * as React from "react";
import { toast } from "react-toastify";
import { Helmet } from "react-helmet";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { ToastMsg } from "../../notifications/Notifications";
import GlobalAppContext from "../../utils/GlobalAppContext";

const FIELD_OPTIONS = [
  { value: "artist_name", label: "Artist Name" },
  { value: "track_name", label: "Track Name" },
  { value: "release_name", label: "Release Name" },
];

const OPERATOR_OPTIONS = [
  { value: "eq", label: "Equals" },
  { value: "neq", label: "Does not equal" },
  { value: "contains", label: "Contains" },
];

export default function SubmissionFilters() {
  const globalContext = React.useContext(GlobalAppContext);
  const { APIService, currentUser, userPreferences } = globalContext;

  const [filters, setFilters] = React.useState<SubmissionFilter[]>(
    userPreferences?.submission_filters?.filters || []
  );

  const [saving, setSaving] = React.useState(false);

  const handleAddFilter = () => {
    const newFilter: SubmissionFilter = {
      action: "ignore",
      conditions: [{ field: "artist_name", operator: "eq", value: "" }],
    };
    setFilters([...filters, newFilter]);
  };

  const handleRemoveFilter = (index: number) => {
    const updatedFilters = [...filters];
    updatedFilters.splice(index, 1);
    setFilters(updatedFilters);
  };

  const handleUpdateCondition = (
    filterIndex: number,
    conditionIndex: number,
    field: string,
    value: string
  ) => {
    const updatedFilters = [...filters];
    updatedFilters[filterIndex].conditions[conditionIndex] = {
      ...updatedFilters[filterIndex].conditions[conditionIndex],
      [field]: value,
    };
    setFilters(updatedFilters);
  };

  const saveSettings = async () => {
    if (!currentUser?.auth_token) {
      toast.error("You must be logged in to update your submission filters");
      return;
    }
    setSaving(true);
    try {
      await APIService.submitSubmissionFilters(currentUser.auth_token, {
        filters,
      });
      toast.success("Saved your submission filters successfully");

      if (userPreferences) {
        userPreferences.submission_filters = { filters };
      }
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Error saving submission filters"
          message={error.toString()}
        />
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Helmet>
        <title>Submission Filters Settings</title>
      </Helmet>
      <h2 className="page-title">Submission Filters</h2>
      <p>
        Configure rules to prevent certain tracks (e.g. podcasts or radio
        broadcasts) from being submitted to ListenBrainz. Listens matching any
        out of these filters will be ignored.
      </p>

      <div className="filters-container mt-4">
        {filters.length === 0 ? (
          <p className="text-muted">No submission filters configured yet.</p>
        ) : (
          filters.map((filter, fIndex) => (
            <div
              key={`filter-${fIndex}`}
              className="card bg-dark text-white mb-3"
            >
              <div className="card-body">
                <div className="d-flex justify-content-between mb-2">
                  <h5>
                    Filter #{fIndex + 1} ({filter.action})
                  </h5>
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    onClick={() => handleRemoveFilter(fIndex)}
                    title="Remove filter"
                  >
                    <FontAwesomeIcon icon={faTrash} />
                  </button>
                </div>

                {filter.conditions.map((condition, cIndex) => (
                  <div
                    key={`filter-${fIndex}-cond-${cIndex}`}
                    className="row mb-2"
                  >
                    <div className="col-md-4">
                      <select
                        className="form-control"
                        value={condition.field}
                        onChange={(e) =>
                          handleUpdateCondition(
                            fIndex,
                            cIndex,
                            "field",
                            e.target.value
                          )
                        }
                      >
                        {FIELD_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-3">
                      <select
                        className="form-control"
                        value={condition.operator}
                        onChange={(e) =>
                          handleUpdateCondition(
                            fIndex,
                            cIndex,
                            "operator",
                            e.target.value
                          )
                        }
                      >
                        {OPERATOR_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-5">
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Value..."
                        value={condition.value}
                        onChange={(e) =>
                          handleUpdateCondition(
                            fIndex,
                            cIndex,
                            "value",
                            e.target.value
                          )
                        }
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 mb-4">
        <button
          type="button"
          className="btn btn-outline-info"
          onClick={handleAddFilter}
        >
          <FontAwesomeIcon icon={faPlus} className="mr-2" /> Add Filter
        </button>
      </div>

      <button
        className="btn btn-lg btn-info"
        type="button"
        onClick={saveSettings}
        disabled={saving}
      >
        {saving ? "Saving..." : "Save Submission Filters"}
      </button>
    </>
  );
}
