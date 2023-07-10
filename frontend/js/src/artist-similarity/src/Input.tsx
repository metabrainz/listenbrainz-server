import React from "react";

interface InputProps {
    onLimitChange: (limit: number) => void;
    onArtistChange: (artist_mbid: string) => void;
}

const Input = (props: InputProps) => {

    const handleInput = (event: React.FormEvent<HTMLFormElement>): void => {
        event.preventDefault();
        const form = event.currentTarget;
        
        var artist_mbid = form.artist_mbid.value;
        var limit = form.limit.value;
        props.onLimitChange(limit);
        props.onArtistChange(artist_mbid);
    }

    return (
        <div>
            <form onSubmit={handleInput}>
                <label>
                    Artist MBID:
                    <input type="text" name="artist_mbid" defaultValue="8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"/>
                </label>
                <label>
                    Size:
                    <input type="text" name="limit" defaultValue="18"/>
                </label>
                <button type="submit">Generate graph</button>
            </form>
        </div>
    );
}

export default Input;