import { ArtistInfoType, RecordingType } from "./Panel";

type WikiReponseType = {
    wikipediaExtract: {
        content: string;
        canonical: string;
        url: string;
        title: string;
        language: string;    
    };
};

type BirthAreaResponseType = {
    "life-span": {
        begin: string;
        end: string;
        ended: boolean;
    };
    area: {
        name: string;
    };
};

type RecordingResponseType = Array<RecordingType>;

const InfoLookup = async (artistMBID: string): Promise<ArtistInfoType> => {
    const ARTIST_URL = `https://musicbrainz.org/artist/${artistMBID}`;
    const WIKI_URL = `${ARTIST_URL}/wikipedia-extract`;
    const BIRTH_AREA_URL = `https://musicbrainz.org/ws/2/artist/${artistMBID}?fmt=json`;
    const RECORDING_URL = `https://test-api.listenbrainz.org/1/popularity/top-recordings-for-artist?artist_mbid=${artistMBID}`;
    var artistInfo: ArtistInfoType;
    try {
        const [wikiData, birthAreaData, topTrackData] = await Promise.all([
            wikiLookup(WIKI_URL),
            birthAreaLookup(BIRTH_AREA_URL),
            topTrackLookup(RECORDING_URL)
        ]);
        // Merge the info in the artistInfo array
        artistInfo = {
            born: birthAreaData.born,
            area: birthAreaData.area,
            wiki: wikiData,
            mbLink: ARTIST_URL,
            topTrack: topTrackData
        }
    } 
    catch (error) {
        alert("Error fetching artist info:");
        throw error;
    }
    return artistInfo;
}

// Lookup birth and area for the artist
const birthAreaLookup = async (BIRTH_AREA_URL: string): Promise<{born: string, area: string}> => {
    const response = await fetch(BIRTH_AREA_URL);
    const data: BirthAreaResponseType = await response.json();
    // Default data in case no info is available
    let birthAreaData = {
        born: "Unknown",
        area: "Unknown"
    }
    // Check life span and begin are not null
    if(data["life-span"] && data["life-span"].begin) {
        let birthData = data["life-span"].begin;
        birthAreaData.born = birthData;
    }
    // Check area and area name are not null
    if(data.area && data.area.name) {
        let areaData = data.area.name;
        birthAreaData.area = areaData;
    }
    return birthAreaData;
}

// Lookup wikipedia extract for the artist
const wikiLookup = async(WIKI_URL: string): Promise<string> => {
    const response = await fetch(WIKI_URL);
    const data: WikiReponseType = await response.json();
    // Default data in case nothing is available
    let wikiData = "No wiki data found.";
    if(data.wikipediaExtract) {
        const htmlParser = new DOMParser();
        let htmlData = htmlParser.parseFromString(data.wikipediaExtract.content, "text/html");
        // Select paragraphs with the actual wiki content i.e. don't have the (.mw-empty-elt) class
        let htmlParagraphs = htmlData.querySelector("p:not(.mw-empty-elt)");
        if(htmlParagraphs && htmlParagraphs.textContent) {
            wikiData = htmlParagraphs.textContent;
        }
    }
    return wikiData;
}

// Lookup for top artist track
const topTrackLookup = async (RECORDING_URL:string): Promise<RecordingType | null> => {
    const response = await fetch(RECORDING_URL);
    const data: RecordingResponseType = await response.json();
    // Default to null
    let topTrackData: RecordingType | null = null;
    if(data.length) {
        // Selecting top track
        topTrackData = data[0];
    }
    return topTrackData;
}

export default InfoLookup;