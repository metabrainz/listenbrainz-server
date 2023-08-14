import { throttle, debounce } from "lodash";
type ArtistType = {
    name: string;
    id: string;
    type?: string;
    country?: string;
}

type ArtistLookupResponseType = {
    created: string;
    count: number;
    offset: number;
    artists: Array<ArtistType>;
}

const artistLookup = async (searchQuery: string) => {
    var resultsArray: Array<ArtistType> = [];
    const LOOKUP_URL = `https://musicbrainz.org/ws/2/artist/?query=artist:${searchQuery}&fmt=json`;
    var data: ArtistLookupResponseType;
    // Fetches the artists from the MusicBrainz API
    try {
        const response = await fetch(LOOKUP_URL);
        data = await response.json();
        resultsArray = data.artists;
    }
    catch(error){
        alert(error);
    }
    return resultsArray;
}
// Old code commented out:
//const throttledArtistLookup = throttle(artistLookup, 800, {leading: false});
//export default throttledArtistLookup;

export default artistLookup;
export type { ArtistType, ArtistLookupResponseType };