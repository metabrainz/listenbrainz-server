import React, { useEffect } from "react";
import SearchDropdown from "./SearchDropdown";
import { throttle, throttle as _throttle } from "lodash";
interface InputProps {
    onLimitChange: (limit: number) => void;
    onArtistChange: (artist_mbid: string) => void;
}

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

const Input = (props: InputProps) => {
    // State to store the user query (input)
    const [searchQuery, setSearchQuery] = React.useState<string>("");
    // State to store the search results (list of artists)
    const [searchResults, setSearchResults] = React.useState<Array<ArtistType>>([]);
    const [limit, setLimit] = React.useState<number>();
    const [artist, setArtist] = React.useState<ArtistType>();
    // The URL for the MusicBrainz API
    const LOOKUP_URL = `http://musicbrainz.org/ws/2/artist/?query=artist:${searchQuery}&fmt=json`;
    const UNDEFINED_PROPERTY = "Unknown";

    // Fetches the artists from the MusicBrainz API
    const fetchArtists = throttle(
        async(): Promise<void> => {
        try {
            const response = await fetch(LOOKUP_URL);
            const data = await response.json();
            setData(data);
        }
        catch(error){
            alert(error);
        }
    }, 500, {leading: false, trailing: true});    
    
    const setData = (dataResponse: ArtistLookupResponseType): void => {
         setSearchResults(dataResponse.artists.map((artist) => {
            return {
                id: artist.id ?? UNDEFINED_PROPERTY,
                type: artist.type ?? UNDEFINED_PROPERTY,
                name: artist.name ?? UNDEFINED_PROPERTY,
                country: artist.country ?? UNDEFINED_PROPERTY,
            };
        }));
    }

    useEffect(() => {
        if(searchQuery && searchQuery.trim() !== ""){
            fetchArtists();
        }
        else{
            setSearchResults([]);
        }
    }, [searchQuery]);
    
    const handleInput = (event: React.FormEvent<HTMLFormElement>): void => {
        event.preventDefault();
        const form = event.currentTarget;
        var artist_mbid = form.artist_mbid.value;
        var limit = form.limit.value;

        props.onLimitChange(limit);
        if(artist?.id !== undefined)
            props.onArtistChange(artist.id);
    }

    return (
        <form 
        onSubmit={handleInput}
        autoComplete="off"
        style={
            {
                display: "flex", 
                flexDirection: "row",
                justifyContent: "left",
                height: "4vh",
                padding: "1vh"
            }
        }
        >
            <div
            style={
                {
                    height: "4vh",
                    width: "20vh",
                }
            }
            onClick={(e) => {const dd = document.getElementById("search-dropdown"); dd?.style.display === "flex" ? dd.style.display = "none" : dd!.style.display = "flex";}}
            >
                <input id="artist-input" style={{height: "inherit", width: "inherit"}} type="search" name="artist_mbid" placeholder="Artist name" onChange={e => setSearchQuery(e.target.value)}/>   
                <SearchDropdown searchResults={searchResults} onArtistChange={setArtist}/>
            </div>
            <input type="text" name="limit" placeholder="Graph size"/>
            <button type="submit">Generate graph</button>
        </form>

    );
}

export default Input;
export type { ArtistType };