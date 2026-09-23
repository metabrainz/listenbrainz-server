import * as React from "react";
import { useQuery } from "@tanstack/react-query";

type Contributor = {
  id: number;
  login: string;
  avatar_url: string;
  html_url: string;
  type: string;
};

async function fetchContributors(signal: AbortSignal): Promise<Contributor[]> {
  const contributors: Contributor[] = [];
  let page = 1;
  let hasNextPage = true;

  while (hasNextPage) {
    // Each response tells us whether another page exists.
    // eslint-disable-next-line no-await-in-loop
    const response = await fetch(
      `https://api.github.com/repos/metabrainz/listenbrainz-server/contributors?per_page=100&page=${page}`,
      { signal, headers: { Accept: "application/vnd.github+json" } }
    );
    if (!response.ok) {
      throw new Error("Unable to load GitHub contributors");
    }
    if (response.status === 204) {
      break;
    }
    // eslint-disable-next-line no-await-in-loop
    const results: Contributor[] = await response.json();
    contributors.push(
      ...results.filter((contributor) => contributor.type === "User")
    );
    hasNextPage = /rel="next"/.test(response.headers.get("Link") ?? "");
    page += 1;
  }

  return contributors;
}

export default function Contributors() {
  const { data: contributors, isPending, isError } = useQuery({
    queryKey: ["github-contributors", "metabrainz/listenbrainz-server"],
    queryFn: ({ signal }) => fetchContributors(signal),
    staleTime: 1000 * 60 * 60 * 24,
    gcTime: 1000 * 60 * 60 * 24,
    retry: false,
    refetchOnWindowFocus: false,
  });

  return (
    <section aria-labelledby="contributors-heading">
      <h2 id="contributors-heading" className="page-title">
        Contributors
      </h2>
      <p>Thanks to everyone who helps us build ListenBrainz!</p>
      {isPending && <p role="status">Loading contributors…</p>}
      {isError && (
        <p role="status">We couldn&apos;t load contributors right now.</p>
      )}
      {contributors && contributors.length > 0 && (
        <ul className="contributors-grid" aria-label="GitHub contributors">
          {contributors.map((contributor) => (
            <li key={contributor.id}>
              <a href={contributor.html_url} title={contributor.login}>
                <img
                  src={contributor.avatar_url}
                  alt={contributor.login}
                  width={64}
                  height={64}
                  loading="lazy"
                />
              </a>
            </li>
          ))}
        </ul>
      )}
      <p>
        <a href="https://github.com/metabrainz/listenbrainz-server/graphs/contributors">
          View contributors on GitHub
        </a>
      </p>
    </section>
  );
}
