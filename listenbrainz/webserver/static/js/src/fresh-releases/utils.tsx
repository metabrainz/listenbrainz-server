import { useEffect, useState } from "react";

export function formatReleaseDate(releaseDate: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  })
    .formatToParts(new Date(Date.parse(releaseDate)))
    .reverse()
    .map((date_parts) => date_parts.value)
    .join("");
}

// Originally from https://usehooks-ts.com/react-hook/use-media-query
export function useMediaQuery(queryStr: string) {
  const getMatches = (query: string): boolean => {
    if (typeof window !== "undefined") {
      return window.matchMedia(query).matches;
    }
    return false;
  };

  const [matches, setMatches] = useState<boolean>(getMatches(queryStr));

  function handleChange() {
    setMatches(getMatches(queryStr));
  }

  useEffect(() => {
    const matchMedia = window.matchMedia(queryStr);
    handleChange();
    matchMedia.addEventListener("change", handleChange);
    return () => {
      matchMedia.removeEventListener("change", handleChange);
    };
  }, [queryStr]);

  return matches;
}
