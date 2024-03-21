import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation, useParams } from "react-router-dom";
import { RouteQuery } from "../utils/Loader";

type ReleaseLoaderData = {
  releaseGroupMBID: string;
};

export default function Release() {
  const location = useLocation();
  const { releaseMBID } = useParams() as { releaseMBID: string };
  const {
    data: { releaseGroupMBID },
  } = useQuery(RouteQuery(["release", releaseMBID], location.pathname)) as {
    data: ReleaseLoaderData;
  };
  return <Navigate to={`/album/${releaseGroupMBID}/`} />;
}
