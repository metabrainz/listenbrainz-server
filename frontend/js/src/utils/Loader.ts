import type { LoaderFunctionArgs, Params } from "react-router-dom";
import { json } from "react-router-dom";
import { isEmpty } from "lodash";
import queryClient from "./QueryClient";
import { getObjectForURLSearchParams } from "./utils";

const RouteLoader = async ({ request }: { request: Request }) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  const data = await response.json();
  if (!response.ok) {
    throw json(data, { status: response.status });
  }
  return data;
};

export default RouteLoader;

const RouteLoaderURL = async (url: string) => {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  const data = await response.json();
  if (!response.ok) {
    throw json(data, { status: response.status });
  }
  return data;
};

export const RouteQuery = (key: any[], url: string) => ({
  queryKey: key,
  queryFn: async () => {
    const data = await RouteLoaderURL(url);
    return data;
  },
});

export const RouteQueryLoader = (
  routeKey: string,
  includeSearchParams = false,
  throwOnError: (response: Response) => boolean = () => true
) => async ({ request, params }: LoaderFunctionArgs) => {
  const keys = [routeKey] as any[];

  // Add params to the keys
  const paramsObject = { ...params };
  if (!isEmpty(paramsObject)) keys.push(paramsObject);

  if (includeSearchParams) {
    // Add search params to the keys
    const searchParams = new URLSearchParams(request.url.split("?")[1]);
    const searchParamsObject = getObjectForURLSearchParams(searchParams);
    keys.push(searchParamsObject);
  }
  try {
    await queryClient.ensureQueryData({
      ...RouteQuery(keys, request.url || ""),
    });
  } catch (response) {
    if (throwOnError(response)) {
      throw response;
    }
  }
  return null;
};
