import * as React from "react";
import { QueryObserverResult, useQuery } from "@tanstack/react-query";
import GlobalAppContext from "./GlobalAppContext";
import type { Flair } from "./constants";

export default function useUserFlairs(userName: string) {
  const { APIService } = React.useContext(GlobalAppContext);
  const data = useQuery({
    queryKey: ["flair"],
    queryFn: () => APIService.getUserFlairs().catch(() => ({})),
    staleTime: Infinity,
  });

  const { data: flairData } = data as QueryObserverResult<
    Record<string, Flair>
  >;
  return flairData?.[userName];
}
