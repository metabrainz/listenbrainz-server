import * as React from "react";
import { Navigate, useLoaderData } from "react-router-dom";

type ReleaseLoaderData = {
  releaseGroupMBID: string;
};

export default function Release() {
  const { releaseGroupMBID } = useLoaderData() as ReleaseLoaderData;
  return <Navigate to={`/album/${releaseGroupMBID}/`} />;
}
