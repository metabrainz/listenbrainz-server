const originalFetch = window.fetch;
const fetchWithRetry = require("fetch-retry")(originalFetch);

const getCoverartFromReleaseMBID = async (
  releaseMBID: string
): Promise<string | undefined> => {
  try {
    const CAAResponse = await fetchWithRetry(
      `https://coverartarchive.org/release/${releaseMBID}`,
      {
        retries: 3,
        retryOn: [429],
        retryDelay(attempt: number) {
          const maxRetryTime = 800;
          const minRetryTime = 400;
          return Math.floor(
            Math.random() * (maxRetryTime - minRetryTime) +
              attempt * minRetryTime
          );
        },
      }
    );
    if (CAAResponse.ok) {
      const body: CoverArtArchiveResponse = await CAAResponse.json();
      if (!body.images?.length) {
        return undefined;
      }
      const frontImage = body.images.find((image) => image.front);

      if (frontImage?.id) {
        const { id } = frontImage;
        return `https://archive.org/download/mbid-${releaseMBID}/mbid-${releaseMBID}-${id}_thumb250.jpg`;
      }

      // No front image? Fallback to whatever the first image is
      const { thumbnails, image } = body.images[0];
      return thumbnails[250] ?? thumbnails.small ?? image;
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn(
      `Couldn't fetch Cover Art Archive entry for ${releaseMBID}`,
      error
    );
  }
  return undefined;
};

const formattedReleaseDate = (releaseDate: string) => {
  return new Intl.DateTimeFormat("default", {
    month: "short",
    day: "numeric",
  })
    .formatToParts(new Date(Date.parse(releaseDate)))
    .reverse()
    .map((date_parts) => date_parts.value)
    .join("");
};

export { getCoverartFromReleaseMBID, formattedReleaseDate };
