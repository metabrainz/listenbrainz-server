const getCoverartFromReleaseMBID = async (
  releaseMBID: string
): Promise<string | undefined> => {
  try {
    const CAAResponse = await fetch(
      `https://coverartarchive.org/release/${releaseMBID}`
    );
    if (CAAResponse.ok) {
      const body: CoverArtArchiveResponse = await CAAResponse.json();
      if (!body.images?.[0]?.thumbnails) {
        return undefined;
      }
      const { thumbnails } = body.images[0];
      return (
        thumbnails[250] ??
        thumbnails.small ??
        // If neither of the above exists, return the first one we find
        // @ts-ignore
        thumbnails[Object.keys(thumbnails)?.[0]]
      );
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
