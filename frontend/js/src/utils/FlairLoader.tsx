import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "./GlobalAppContext";

function FlairLoader() {
  const { APIService } = React.useContext(GlobalAppContext);
  const data = useQuery({
    queryKey: ["flair"],
    queryFn: () => APIService.getUserFlairs().catch(() => ({})),
    staleTime: Infinity,
  });
  return null;
}

export default React.memo(FlairLoader);
