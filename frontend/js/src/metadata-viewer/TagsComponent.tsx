import * as React from "react";

export default function TagsComponent(props: {
  tags?: Array<ArtistTag | RecordingTag>;
}) {
  const { tags } = props;
  return (
    <div className="tags-wrapper content-box">
      <div className="tags">
        {tags?.length ? (
          tags
            .filter((tag) => tag.genre_mbid)
            .sort((t1, t2) => t2.count - t1.count)
            .map((tag) => (
              <span key={tag.tag + tag.count} className="badge">
                <a
                  href={`https://musicbrainz.org/tag/${tag.tag}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {tag.tag}
                </a>
              </span>
            ))
        ) : (
          <span>Be the first to add a tag</span>
        )}
      </div>
      {/* <div className="add-tag">
        <button className="btn btn-xs btn-outline" type="button">
          + Add tag
        </button>
      </div> */}
    </div>
  );
}
