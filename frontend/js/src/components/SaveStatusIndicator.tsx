import React from "react";

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface SaveStatusIndicatorProps {
  status: SaveStatus;
  errorMessage?: string;
}

export default function SaveStatusIndicator({
  status,
  errorMessage,
}: SaveStatusIndicatorProps) {
  if (status === "idle") {
    return null;
  }

  let alertClass = "alert-info";
  if (status === "saved") {
    alertClass = "alert-success";
  } else if (status === "error") {
    alertClass = "alert-danger";
  }

  return (
    <div className={`alert ${alertClass} mb-3`} style={{ padding: "8px 12px" }}>
      {status === "saving" && (
        <span>
          <i className="fa fa-spinner fa-spin" /> Saving...
        </span>
      )}
      {status === "saved" && (
        <span>
          <i className="fa fa-check" /> Changes saved automatically
        </span>
      )}
      {status === "error" && (
        <span>
          <i className="fa fa-exclamation-triangle" /> Auto-save failed
          {errorMessage ? `: ${errorMessage}` : ""}
        </span>
      )}
    </div>
  );
}
