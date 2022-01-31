import React, { useEffect, useState } from "react";

const Blog = () => {
  const [blogDetails, setBlogDetails] = useState([{}]);

  const fetchBlogDetails = async () => {
    let response: any = await fetch(
      `https://public-api.wordpress.com/rest/v1.1/sites/blog.metabrainz.org/posts/`
    );
    response = await response.json();
    const objectArray: any = [];
    for (let postIndex = 0; postIndex <= 6; postIndex += 1) {
      const object: any = {};
      object.id = response.posts[postIndex].ID;
      object.title = response.posts[postIndex].title;
      object.link = response.posts[postIndex].URL;
      objectArray.push(object);
    }
    setBlogDetails(objectArray);
  };
  useEffect(() => {
    fetchBlogDetails();
  }, []);

  return (
    <div className="card">
      <div className="panel-heading center-p">
        <strong>News & Updates</strong>
      </div>
      <div className="panel-body">
        {blogDetails.map((post: any) => (
          <li>
            <a
              href={post.link}
              target="_blank"
              rel="noopener noreferrer"
              className="card-link"
            >
              {post.title}
            </a>
          </li>
        ))}
      </div>
      <div className="panel-footer center-p">
        <a
          href="https://twitter.com/MusicBrainz"
          target="_blank"
          rel="noopener noreferrer"
          className="card-link"
          style={{ marginRight: "12px" }}
        >
          Twitter
        </a>
        <a
          href="https://blog.metabrainz.org"
          className="card-link"
          target="_blank"
          rel="noopener noreferrer"
          style={{ marginLeft: "8px", marginRight: "8px" }}
        >
          Blog
        </a>
        <a
          href="https://community.metabrainz.org"
          className="card-link"
          target="_blank"
          rel="noopener noreferrer"
          style={{ marginLeft: "12px" }}
        >
          Community Forum
        </a>
      </div>
    </div>
  );
};

export default Blog;
