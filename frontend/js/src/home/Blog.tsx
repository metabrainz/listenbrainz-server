import React, { useEffect, useState } from "react";

function Blog({ apiUrl }: { apiUrl: string }) {
  const [blogDetails, setBlogDetails] = useState<object[]>();

  const fetchBlogDetails = async () => {
    try {
      let response: any = await fetch(`${window.location.origin}/blog-data/`);
      if (response.status === 200) {
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
      }
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e);
    }
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
        {blogDetails &&
          blogDetails.map((post: any) => (
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
        {!blogDetails && <li>None yet...</li>}
      </div>
      <div className="panel-footer center-p">
        <a
          href="https://twitter.com/ListenBrainz"
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
}

export default Blog;
