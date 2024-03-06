import { json } from "react-router-dom";

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
