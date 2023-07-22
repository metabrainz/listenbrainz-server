import { throttle } from "lodash";
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

const ArtistLookup = throttle(async (searchQuery: string):  Promise<Array<ArtistType>>=> {
    var resultsArray: Array<ArtistType> = [];
    const UNDEFINED_PROPERTY = "Unknown";
    const LOOKUP_URL = `https://musicbrainz.org/ws/2/artist/?query=artist:${searchQuery}&fmt=json`;
    var data: ArtistLookupResponseType;
    // Fetches the artists from the MusicBrainz API
    try {
        const response = await fetch(LOOKUP_URL);
        data = await response.json();   
    }
    catch(error){
        alert(error);
        // Do we need to return something here?
        data = {
            created: "",
            count: 0,
            offset: 0,
            artists: []
        };
    }
    return data.artists;
}, 500);

export default ArtistLookup;
export type { ArtistType, ArtistLookupResponseType };