import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { RouteQuery } from "../utils/Loader";

type ReleaseLoaderData = {
  releaseGroupMBID: string;
};

export default function Release() {
  const location = useLocation();
  const params = useParams() as { releaseMBID: string };
  const { data } = useQuery<ReleaseLoaderData>(
    RouteQuery(["release", params], location.pathname)
  );
  const { releaseGroupMBID } = data || {};
  return <Navigate to={`/album/${releaseGroupMBID}/`} replace />;
}
