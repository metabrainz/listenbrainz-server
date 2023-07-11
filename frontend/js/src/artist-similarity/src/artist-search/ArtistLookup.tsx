import React from "react";
import { ArtistType } from "./SearchBox";

/*type ArtistType = {
    id: string;
    type?: string;
    name: string;
    country?: string;
}*/

type ArtistLookupResponseType = {
    created: string;
    count: number;
    offset: number;
    artists: Array<ArtistType>;
}

const ArtistLookup = (searchQuery: string): Array<ArtistType> => {
    var resultsArray: Array<ArtistType> = [];
    const LOOKUP_URL = `http://musicbrainz.org/ws/2/artist/?query=artist:${searchQuery}&fmt=json`;
    const fetchArtists = async (): Promise<void> => {
        try {
            const response = await fetch(LOOKUP_URL);
            const data = await response.json();
            processData(data);
        }
        catch(error){
            alert(error);
        }
    }
    
    const processData = (dataResponse: ArtistLookupResponseType): void => {
       
        resultsArray = dataResponse.artists.map((artist) => {
            return {
                id: artist.id,
                type: artist.type ?? "Unknown",
                name: artist.name,
                country: artist.country ?? "Unknown",
            };
        });
    }
    console.log(resultsArray);
    return (fetchArtists(), resultsArray);
}
export default ArtistLookup;