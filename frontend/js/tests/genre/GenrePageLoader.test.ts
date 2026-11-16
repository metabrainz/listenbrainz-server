import { matchRoutes } from "react-router";
import { GenrePageLoader } from "../../src/genre/Genre";
import queryClient from "../../src/utils/QueryClient";

const genre = { name: "drum & bass" };
const genreMBID = "0e3fc579-2d24-4f20-9dae-736e1ec78798";
const canonicalPath = "/genre/drum%20%26%20bass/";
const load = (path: string) => {
  const [match] = matchRoutes([{ path: "/genre/:genre/" }], path)!;
  return GenrePageLoader({ params: match.params });
};

describe("GenrePageLoader", () => {
  let fetchMock: jest.SpyInstance;

  beforeEach(() => {
    fetchMock = jest.spyOn(globalThis, "fetch").mockImplementation(
      async () => new Response(JSON.stringify({ genre, genre_mbid: genreMBID }))
    );
  });

  afterEach(() => {
    fetchMock.mockRestore();
    queryClient.clear();
  });

  it("loads a canonical genre URL without redirecting to itself", async () => {
    await expect(load(canonicalPath)).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(canonicalPath, expect.any(Object));
  });

  it("redirects a genre MBID once and reuses the response at the canonical name", async () => {
    const response = await load(`/genre/${genreMBID}/`).catch(
      (error: Response) => error
    );
    expect(response?.status).toBe(302);
    expect(response?.headers.get("Location")).toBe(canonicalPath);
    await expect(load(canonicalPath)).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
