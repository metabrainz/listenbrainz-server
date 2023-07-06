import React, {useState, useEffect} from "react";
import Graph from "./Graph";
import Input from "./Input";

type ColorType = {
    red: number;
    green: number;
    blue: number;
    opacity: number;
    mixed: string;
}

type ArtistType = {
    artist_mbid: string;
    name: string;
    comment: string;
    type: string;
    gender: string;
    score?: number;
    reference_mbid?: string;
}
    
type MarkupResponseType = {
    data: string;
    type: "markup";
}

type DatasetResponseType = {
    columns: Array<string>;
    data: Array<ArtistType>;
    type: "dataset";
}

type ApiResponseType = MarkupResponseType | DatasetResponseType;

const Color = (red: number, green: number, blue: number): ColorType => {
    return {
        red: red,
        green: green,
        blue: blue,
        opacity: 1.0,
        mixed: "rgba(" + red + "," + green + "," + blue + "," + 1.0 + ")",
    }
}

const changeOpacity = (color: ColorType, opacity: number): ColorType => {
    return {
        red: color.red,
        green: color.green,
        blue: color.blue,
        opacity: opacity,
        mixed: "rgba(" + color.red + "," + color.green + "," + color.blue + "," + opacity + ")",
    }
}

const colorGenerator = (): ColorType => {
    var red = Math.floor(Math.random() * 200);
    var green = Math.floor(Math.random() * 200);
    var blue  = Math.floor(Math.random() * 200);

    return Color(red, green, blue);
}

const mixColor = (color1: ColorType, color2: ColorType, weight: number): ColorType => {
    var red = Math.floor((color2.red - color1.red) * weight + color1.red);
    var green = Math.floor((color2.green - color1.green) * weight + color1.green);
    var blue = Math.floor((color2.blue - color1.blue) * weight + color1.blue);          
    var opacity = Math.floor((color2.opacity - color1.opacity) * weight + color1.opacity);

    return Color(red, green, blue);
}

const Data = () => {
    const LIMIT_VALUE = 18;
    const BASE_URL = "https://labs.api.listenbrainz.org/similar-artists/json?algorithm=session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30&artist_mbid=";
    
    var artist_mbid = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11";
    var color1 = colorGenerator();
    var color2 = colorGenerator();

    const [similarArtists, setSimilarArtists] = useState({} as DatasetResponseType);
    const [artist, setArtist] = useState({} as DatasetResponseType);
    const [limit, setLimit] = useState(LIMIT_VALUE);
    const [colors, setColors] = useState([color1, color2]);
    
    var transformedArtists = {};
    var scoreList: Array<number> = [];
    var similarArtistsList: Array<ArtistType> = [];
    var mainArtist: ArtistType = {} as ArtistType;
    var minScore = 0;
    
    const fetchData = (artist_mbid: string): void => {
        fetch(BASE_URL + artist_mbid)
        .then((response) => response.json())
        .then((data) => processData(data))   
    }
    
    const processData = (data: Array<ApiResponseType>): void => {
        let mainArtist = data[1] as DatasetResponseType;
        setArtist(mainArtist);

        let similarArtists = data[3] as DatasetResponseType;
        setSimilarArtists(similarArtists);
        setColors([mixColor(colors[0], colors[1], 0.3), color2]);
    }
    
    useEffect(() => {
        fetchData(artist_mbid);
        setColors([color1, color2]);
    }, []);

    similarArtistsList = similarArtists && similarArtists.data && (similarArtists.data.map((artist: any) => artist));
    similarArtistsList = similarArtistsList && similarArtistsList.splice(0, limit);
    
    mainArtist = artist && artist.data && artist.data[0];
    similarArtistsList && similarArtistsList.push(mainArtist);

    // Calculating minScore for normalization which is always the last element of the array (because it's sorted)
    minScore = similarArtistsList && similarArtistsList[LIMIT_VALUE - 1].score as number;
    minScore = Math.sqrt(minScore);

    transformedArtists = similarArtistsList && {
        
        "nodes": similarArtistsList.map((artist: ArtistType, index: number) => {

            if(artist !== mainArtist) {
                var computedScore = minScore / Math.sqrt(artist.score as number);
                var computedColor = mixColor(colors[0], colors[1], (index / LIMIT_VALUE * computedScore));
                scoreList.push(computedScore);
            }
            
            else{
                computedColor = colors[0];
                similarArtistsList.pop();
            }

            return {
                "id": artist.name,
                "artist_mbid": artist.artist_mbid,
                "size": artist.artist_mbid === mainArtist.artist_mbid ? 150 : 85,
                "color": computedColor.mixed,
                "colorObject": computedColor,
                "seed": artist.artist_mbid === mainArtist.artist_mbid ? 1 : 0,
                "score": artist.score
            };
        }),

        "links": similarArtistsList.map((artist: ArtistType, index: number) => {
            return {
                "source": mainArtist.name,
                "target": artist.name,
                "distance": (artist.artist_mbid != mainArtist.artist_mbid ? scoreList[index] * 250 : 0),
                "strength": artist.score as number < 5000 ? 2 : artist.score as number < 6000 ? 4 : 8,
                };
        }),
    }

    var backgroundColor = `linear-gradient(` + changeOpacity(colors[1], 0.2).mixed + `,` + changeOpacity(colors[0], 0.2).mixed + `)`;
    
    return (
        <div>
            <Input fetchData={fetchData} setLimit={setLimit}/>
            <Graph data={transformedArtists} fetchData={fetchData} backgroundColor={backgroundColor}/>
        </div>
    );
}

export default Data;