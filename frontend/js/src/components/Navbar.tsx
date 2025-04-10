import React from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import Username from "../common/Username";

function Navbar() {
  const { currentUser } = React.useContext(GlobalAppContext);
  const navigate = useNavigate();

  const [searchTerm, setSearchTerm] = React.useState("");

  const toggleSidebarButton = React.useRef<HTMLButtonElement>(null);

  const toggleSidebar = () => {
    if (
      toggleSidebarButton.current &&
      getComputedStyle(toggleSidebarButton.current).display !== "none"
    ) {
      toggleSidebarButton.current.click();
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const searchInput = searchTerm;
    if (!searchInput) {
      return;
    }
    setSearchTerm("");
    toggleSidebar();
    navigate(`/search/?search_term=${searchInput}`);
  };

  return (
    <nav role="navigation">
      <div className="navbar-header">
        <button
          type="button"
          className="navbar-toggle collapsed"
          data-toggle="collapse"
          data-target="#side-nav,#side-nav-overlay"
          ref={toggleSidebarButton}
        >
          <span className="sr-only">Toggle navigation</span>
          <span className="icon-bar" />
          <span className="icon-bar" />
          <span className="icon-bar" />
        </button>
        <Link
          className="navbar-logo"
          to={
            currentUser?.name
              ? `/user/${currentUser.name}/`
              : "/?redirect=false"
          }
          onClick={toggleSidebar}
        >
          <img
            src="/static/img/navbar_logo.svg"
            alt="ListenBrainz"
            height="31"
          />
        </Link>
      </div>

      <div id="side-nav" className="collapse">
        <Link
          className="navbar-logo"
          to={
            currentUser?.name
              ? `/user/${currentUser.name}/`
              : "/?redirect=false"
          }
          onClick={toggleSidebar}
        >
          <img
            src="/static/img/listenbrainz_logo_icon.svg"
            alt="ListenBrainz"
          />
        </Link>
        <div className="main-nav">
          {currentUser?.name ? (
            <>
              <NavLink to="/feed/" onClick={toggleSidebar}>
                Feed
              </NavLink>
              <NavLink
                to={`/user/${currentUser.name}/`}
                onClick={toggleSidebar}
              >
                Dashboard
              </NavLink>
            </>
          ) : (
            <>
              <NavLink to="/recent/" onClick={toggleSidebar}>
                Feed
              </NavLink>
              <NavLink to="/statistics/" onClick={toggleSidebar}>
                Dashboard
              </NavLink>
            </>
          )}
          <NavLink to="/explore/" onClick={toggleSidebar}>
            Explore
          </NavLink>
        </div>

        <div className="navbar-bottom">
          {currentUser?.name ? (
            <>
              <Username
                username={currentUser.name}
                hideLink
                elementType="div"
                className="username"
              />
              <a href="/login/logout/">Logout</a>
              <NavLink to="/settings/" onClick={toggleSidebar}>
                Settings
              </NavLink>
            </>
          ) : (
            <Link to="/login/" onClick={toggleSidebar}>
              Sign in
            </Link>
          )}
          <NavLink to="/about/" onClick={toggleSidebar}>
            About
          </NavLink>
          <NavLink to="/donors/" onClick={toggleSidebar}>
            Donations
          </NavLink>
          <a
            href="https://community.metabrainz.org/c/listenbrainz"
            target="_blank"
            rel="noopener noreferrer"
          >
            Community
          </a>
          <form className="search-bar" role="search" onSubmit={handleSubmit}>
            <input
              type="text"
              name="search_term"
              className="form-control input-sm"
              placeholder="Search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              required
            />
            <button type="submit">
              <FontAwesomeIcon icon={faMagnifyingGlass} />
            </button>
          </form>
        </div>
        <div className="mobile-nav-fix" />
      </div>
      <div
        id="side-nav-overlay"
        className="collapse"
        data-toggle="collapse"
        data-target="#side-nav,#side-nav-overlay"
      />
    </nav>
  );
}

export default Navbar;
