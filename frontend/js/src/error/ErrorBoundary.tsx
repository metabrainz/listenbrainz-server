import React from "react";
import { Helmet } from "react-helmet";
import { isRouteErrorResponse, useRouteError } from "react-router-dom";

const ErrorStatusMessage: { [key: number]: string } = {
  400: "Invalid request",
  401: "Unauthorized",
  403: "Access denied",
  404: "Page not found",
  413: "Filesize limit exceeded",
  500: "Internal server error",
  503: "Service unavailable",
};

type RouteError = {
  status?: number;
  message?: string;
  data?: any;
};

export function ErrorBoundary() {
  const error = useRouteError() as RouteError;
  const errorStatus = error.status || 500;
  const errorStatusMessage = ErrorStatusMessage[errorStatus] || "Error";

  const errorMessage = error.data?.error || error.message || errorStatusMessage;

  return isRouteErrorResponse(error) ? (
    <>
      <Helmet>
        <title>{errorStatusMessage}</title>
      </Helmet>
      <h2 className="page-title">{errorStatusMessage}</h2>
      <p>
        <code>{`${errorStatus}: ${errorMessage}`}</code>
      </p>
      <p>
        <a href="/">Back to home page</a>
      </p>
    </>
  ) : (
    <>
      <Helmet>
        <title>Error</title>
      </Helmet>
      <h2 className="page-title">Error Occured!</h2>
    </>
  );
}

export default ErrorBoundary;
