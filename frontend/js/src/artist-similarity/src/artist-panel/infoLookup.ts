import { ArtistInfoType } from "./Panel";
type WikiReponseType = {
    wikipediaExtract: WikiExtractType;
};
type WikiExtractType = {
    content: string;
    canonical: string;
    url: string;
    title: string;
    language: string;
}

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

const InfoLookup = async (artistMBID: string): Promise<Array<string>> => {
    const BASEURL = `https://musicbrainz.org/artist/${artistMBID}`;
    const WIKI_URL = `${BASEURL}/wikipedia-extract`;
    const BIRTH_AREA_URL = `https://musicbrainz.org/ws/2/artist/${artistMBID}?fmt=json`;
    var artistInfo: Array<string> = ["Hello"];
    try {
        const [wikiData, birthAreaData] = await Promise.all([
            wikiLookup(WIKI_URL),
            birthAreaLookup(BIRTH_AREA_URL),
        ]);

        // Merge the info in the artistInfo array
        artistInfo = [wikiData, ...birthAreaData];
    } catch (error) {
        alert("Error fetching artist info:");
        throw error;
    }
    
    return artistInfo;
}

// Lookup wikipedia extract for the artist
const wikiLookup = async(WIKI_URL: string): Promise<string> => {
    const response = await fetch(WIKI_URL);
    const data: WikiReponseType = await response.json();
    let wikiData = "No wiki data found.";
    if(data.wikipediaExtract) {
        const htmlParser = new DOMParser();
        let htmlData = htmlParser.parseFromString(data.wikipediaExtract.content, "text/html");
        // Select paragraphs with the actual wiki content
        let htmlParagraphs = htmlData.querySelector("p:not(.mw-empty-elt)");
        if(htmlParagraphs && htmlParagraphs.textContent) {
            wikiData = htmlParagraphs.textContent;
        }
    }
    return wikiData;
}

// Lookup birth and area for the artist
const birthAreaLookup = async (BIRTH_AREA_URL: string): Promise<Array<string>> => {
    const response = await fetch(BIRTH_AREA_URL);
    const data: BirthAreaResponseType = await response.json();
    let birthAreaData = ["Unknown", "Unknown"];
    // Check life span and begin are not null
    if(data["life-span"] && data["life-span"].begin) {
        let birthData = data["life-span"].begin;
        birthAreaData[0] = birthData;
    }
    // Check area and area name are not null
    if(data.area && data.area.name) {
        let areaData = data.area.name;
        birthAreaData[1] = areaData;
    }
    return birthAreaData;
}

export default InfoLookup;
/**
 * const lookup = async () => {
        if(props.artist) {
            ARTIST_URL = `https://musicbrainz.org/artist/${props.artist.artist_mbid}`;
            WIKI_URL = `${ARTIST_URL}/wikipedia-extract`;
            const response = await fetch(WIKI_URL);
            const data = await response.json();
            let wikiData = data.wikipediaExtract.content;
            const parser = new DOMParser();
            const doc = parser.parseFromString(wikiData, 'text/html');
            let paragraphs = Array.from(doc.querySelectorAll('p')).map((p) => p.textContent);
            let wikipediaExtract;
            if(paragraphs.length > 1) {
                wikipediaExtract = (paragraphs[1]! + paragraphs[2]!);
            }
            let newArtistInfo: ArtistInfoType = {
                name: props.artist.name;
                type: props.artist.type;
                born

            }
        }    
    }

 */