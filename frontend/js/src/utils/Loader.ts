import type { LoaderFunctionArgs, Params } from "react-router-dom";
import { json } from "react-router-dom";
import _ from "lodash";
import queryClient from "./QueryClient";

const RouteLoader = async ({ request }: { request: Request }) => {
  const response = await fetch(request.url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
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
      "Content-Type": "application/json",
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

export const RouteQueryLoader = (routeKey: string) => async ({
  request,
  params,
}: LoaderFunctionArgs) => {
  const keys = [routeKey] as any[];

  // Add params to the keys
  const paramsObject = { ...params };
  if (!_.isEmpty(paramsObject)) keys.push(paramsObject);

  // Add search params to the keys
  const searchParams = new URLSearchParams(request.url.split("?")[1]);
  const searchParamsObject = {} as { [key: string]: string };
  searchParams.forEach((value, key) => {
    searchParamsObject[key] = value;
  });
  if (!_.isEmpty(searchParamsObject)) {
    keys.push(searchParamsObject);
  }

  await queryClient.ensureQueryData(RouteQuery(keys, request.url || ""));
  return null;
};
