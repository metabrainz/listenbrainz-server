import type { Params } from "react-router-dom";
import { json } from "react-router-dom";
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

export const RouteQuery = (key: string[], url: string) => ({
  queryKey: key,
  queryFn: async () => {
    const data = await RouteLoaderURL(url);
    return data;
  },
});

export const RouteQueryLoader = (key: string[]) => async ({
  request,
  params,
}: {
  request: Request;
  params: Params<string>;
}) => {
  if (params && Object.keys(params).length) {
    const paramsValues = Object.values(params);
    paramsValues.forEach((value) => {
      if (typeof value === "string") {
        if (!key.includes(value)) {
          key.push(value);
        }
      }
    });
  }

  await queryClient.ensureQueryData(RouteQuery(key, request.url || ""));
  return null;
};
