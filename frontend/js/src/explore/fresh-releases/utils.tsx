import { isValid } from "date-fns";
import { useEffect, useState } from "react";

export function getKeyForOrder(
  releaseOrder: string,
  release: FreshReleaseItem
): string {
  switch (releaseOrder) {
    case "release_date":
      // Use the raw date string as the key (locale-independent, always consistent)
      return release.release_date ?? "-";
    case "artist_credit_name":
    case "release_name":
      // Always uppercase first character to avoid case-split duplicates
      return (release[releaseOrder] ?? "").charAt(0).toUpperCase();
    case "confidence":
      // Round to 1 dp — raw floats (0.50001 vs 0.5) create spurious duplicate groups
      return String(Math.round((release[releaseOrder] ?? 0) * 10) / 10);
    default:
      return "";
  }
}

export function formatReleaseDate(
  releaseDate: string,
  formatOptions: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
  }
) {
  if (!releaseDate || !isValid(new Date(releaseDate))) {
    return "-";
  }
  return new Intl.DateTimeFormat(undefined, formatOptions).format(
    new Date(Date.parse(releaseDate))
  );
}

export function formatListenCount(listenCount: number) {
  if (listenCount >= 1e3 && listenCount < 1e6)
    return `${+(listenCount / 1e3).toFixed(1)}K`;
  if (listenCount >= 1e6 && listenCount < 1e9)
    return `${+(listenCount / 1e6).toFixed(1)}M`;
  if (listenCount >= 1e9 && listenCount < 1e12)
    return `${+(listenCount / 1e9).toFixed(1)}B`;
  if (listenCount >= 1e12) return `${+(listenCount / 1e12).toFixed(1)}T`;

  return listenCount;
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

  useEffect(() => {
    const matchMedia = window.matchMedia(queryStr);
    const handleChange = () => setMatches(getMatches(queryStr));
    handleChange();
    matchMedia.addEventListener("change", handleChange);
    return () => {
      matchMedia.removeEventListener("change", handleChange);
    };
  }, [queryStr]);

  return matches;
}
