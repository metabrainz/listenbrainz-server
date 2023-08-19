type ArtistType = {
  name: string;
  id: string;
  type?: string;
  country?: string;
};

type ArtistLookupResponseType = {
  created: string;
  count: number;
  offset: number;
  artists: Array<ArtistType>;
};

const artistLookup = async (searchQuery: string) => {
  let resultsArray: Array<ArtistType> = [];
  const LOOKUP_URL = `https://musicbrainz.org/ws/2/artist/?query=artist:${searchQuery}&fmt=json`;
  // Fetches the artists from the MusicBrainz API
  try {
    const response = await fetch(LOOKUP_URL);
    if (!response.ok) {
      throw Error();
    }
    const data: ArtistLookupResponseType = await response.json();
    resultsArray = data.artists;
  } catch (error) {
    throw new Error(
      "An error occured while looking up artists. Please try again later"
    );
  }
  return resultsArray;
};

export default artistLookup;
export type { ArtistType, ArtistLookupResponseType };
