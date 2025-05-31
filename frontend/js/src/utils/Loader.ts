import type { LoaderFunctionArgs } from "react-router";
import { data } from "react-router";
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
  const responseData = await response.json();
  if (!response.ok) {
    throw data(responseData, { status: response.status });
  }
  return responseData;
};

export default RouteLoader;

const RouteLoaderURL = async (url: string) => {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  const responseData = await response.json();
  if (!response.ok) {
    throw data(responseData, { status: response.status });
  }
  return responseData;
};

export const RouteQuery = (key: any[], url: string) => ({
  queryKey: key,
  queryFn: async () => {
    const responseData = await RouteLoaderURL(url);
    return responseData;
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
