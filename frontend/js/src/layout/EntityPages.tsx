import React from "react";
import { Outlet, ScrollRestoration, useNavigate } from "react-router-dom";

export default function EntityPageLayout() {
  const navigate = useNavigate();

  const goBack = () => {
    navigate(-1);
  };

  return (
    <>
      <ScrollRestoration />
      <div className="secondary-nav">
        <ol className="breadcrumb">
          <li>
            <button type="button" onClick={goBack} style={{ border: 0 }}>
              ← Back
            </button>
          </li>
        </ol>
      </div>
      <Outlet />
    </>
  );
}
