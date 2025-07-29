import * as React from "react";
import { Navigate, useParams } from "react-router";

export default function Recording() {
  const { recordingMBID } = useParams();
  return <Navigate to={`/track/${recordingMBID}/`} replace />;
}
