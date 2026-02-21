import React, { useState, useEffect } from "react";
import { useParams } from "react-router";
import Loader from "../../components/Loader";

type SortOption = "listeners" | "listens" | "score" | "random";

export default function GenrePage() {
  const { genreName } = useParams<{ genreName: string }>();
  const [activeTab, setActiveTab] = useState<"artists" | "albums" | "tracks">(
    "artists"
  );
  const [sortMethod, setSortMethod] = useState<SortOption>("listeners");

  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(false);

    const url = `/1/explore/genre/${genreName}/${activeTab}?sort=${sortMethod}`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("HTTP error");
        return res.json();
      })
      .then((json) => {
        if (isMounted) {
          setData(json);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error("Failed to fetch:", err);
          setError(true);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [genreName, activeTab, sortMethod]);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const renderContent = () => {
    if (isLoading) return <Loader isLoading />;
    if (error)
      return (
        <div className="alert alert-danger mt-4">
          Failed to load genre data.
        </div>
      );

    const items = data?.payload?.[activeTab] || [];
    if (items.length === 0)
      return (
        <div className="mt-4">
          No matching {activeTab} found for this genre.
        </div>
      );

    return (
      <div className="table-responsive mt-4">
        <table className="table table-striped">
          <thead>
            <tr>
              <th>Name</th>
              {activeTab !== "artists" && <th>Artist</th>}
              <th>Score</th>
              <th>Listeners</th>
              <th>Listens</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: any) => (
              <tr key={item.mbid}>
                <td>
                  <strong>{item.name}</strong>
                </td>
                {activeTab !== "artists" && <td>{item.artist_name}</td>}
                <td>{item.score}</td>
                <td>{formatNumber(item.listeners)}</td>
                <td>{formatNumber(item.listens)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="container mt-4 genre-page">
      <h1>
        Genre: <span className="text-capitalize">{genreName}</span>
      </h1>
      <p className="lead">Explore top music tagged with {genreName}.</p>

      <div className="d-flex justify-content-between align-items-center mb-3">
        <ul className="nav nav-tabs border-bottom-0">
          <li className="nav-item">
            <button
              type="button"
              className={`nav-link ${activeTab === "artists" ? "active" : ""}`}
              onClick={() => setActiveTab("artists")}
            >
              Artists
            </button>
          </li>
          <li className="nav-item">
            <button
              type="button"
              className={`nav-link ${activeTab === "albums" ? "active" : ""}`}
              onClick={() => setActiveTab("albums")}
            >
              Albums
            </button>
          </li>
          <li className="nav-item">
            <button
              type="button"
              className={`nav-link ${activeTab === "tracks" ? "active" : ""}`}
              onClick={() => setActiveTab("tracks")}
            >
              Tracks
            </button>
          </li>
        </ul>
        <div className="sort-controls d-flex align-items-center">
          <label htmlFor="sortMethodSelect" className="me-2 mb-0">
            Sort by:
          </label>
          <select
            id="sortMethodSelect"
            className="form-select w-auto"
            value={sortMethod}
            onChange={(e) => setSortMethod(e.target.value as SortOption)}
          >
            <option value="listeners">Listeners</option>
            <option value="listens">Listens</option>
            <option value="score">Tag Score</option>
            <option value="random">Random</option>
          </select>
        </div>
      </div>

      <div className="tab-content" style={{ minHeight: "300px" }}>
        {renderContent()}
      </div>
    </div>
  );
}
