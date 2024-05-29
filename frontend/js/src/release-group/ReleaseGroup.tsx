import * as React from "react";
import { Navigate, useParams } from "react-router-dom";

export default function ReleaseGroup() {
  const { releaseGroupMBID } = useParams();
  return <Navigate to={`/album/${releaseGroupMBID}/`} replace />;
}
