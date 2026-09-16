import React from "react";
import { Link, NavLink, useNavigate } from "react-router";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import Username from "../common/Username";
import buildAuthUrl from "../utils/auth";

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
    navigate(`/search/?search_term=${encodeURIComponent(searchInput)}`);
  };
  const encodedUsername = currentUser?.name
    ? encodeURIComponent(currentUser.name)
    : undefined;

  return (
    <nav role="navigation">
      <div className="navbar navbar-light navbar-header">
        <button
          type="button"
          className="navbar-toggler"
          data-bs-toggle="collapse"
          data-bs-target="#side-nav,#side-nav-overlay"
          ref={toggleSidebarButton}
        >
          <span className="navbar-toggler-icon" />
        </button>
        <Link
          className="navbar-logo"
          to={
            currentUser?.name ? `/user/${encodedUsername}/` : "/?redirect=false"
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
        <form className="search-bar" role="search" onSubmit={handleSubmit}>
          <input
            type="text"
            name="search_term"
            className="form-control form-control-sm"
            placeholder="Search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            required
          />
          <button type="submit">
            <FontAwesomeIcon icon={faMagnifyingGlass} />
          </button>
        </form>
        <div className="sidebar-nav">
          <Link
            className="navbar-logo"
            to={
              currentUser?.name
                ? `/user/${encodedUsername}/`
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
                  to={`/user/${encodedUsername}/`}
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
              <>
                <a href={buildAuthUrl("login")} onClick={toggleSidebar}>
                  Sign in
                </a>
                <a href={buildAuthUrl("register")} onClick={toggleSidebar}>
                  Create Account
                </a>
              </>
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
          </div>
          <div className="mobile-nav-fix" />
        </div>
      </div>
      <div
        id="side-nav-overlay"
        className="collapse"
        data-bs-toggle="collapse"
        data-bs-target="#side-nav,#side-nav-overlay"
      />
    </nav>
  );
}

export default Navbar;
