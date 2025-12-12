import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCircleChevronLeft,
  faCircleChevronRight,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type YIMFriendsProps = {
  followingList: string[];
  userName: string;
  year: number;
};
export default function YIMFriends({
  followingList,
  userName,
  year,
}: YIMFriendsProps) {
  const { currentUser } = React.useContext(GlobalAppContext);

  const buddiesScrollContainer = React.useRef<HTMLDivElement | null>(null);
  const manualScroll: React.ReactEventHandler<HTMLElement> = (event) => {
    if (!buddiesScrollContainer?.current) {
      return;
    }
    if (event?.currentTarget.classList.contains("forward")) {
      buddiesScrollContainer.current.scrollBy({
        left: 330,
        top: 0,
        behavior: "smooth",
      });
    } else {
      buddiesScrollContainer.current.scrollBy({
        left: -330,
        top: 0,
        behavior: "smooth",
      });
    }
  };
  const isCurrentUser = userName === currentUser?.name;
  const yourOrUsersName = isCurrentUser ? "your" : `${userName}'s`;
  return (
    <div className="section">
      <div className="header">
        Browse {yourOrUsersName} friend&apos;s Year in Music
      </div>
      <div id="buddies">
        <button
          className="btn-icon btn-transparent backward"
          type="button"
          onClick={manualScroll}
        >
          <FontAwesomeIcon icon={faCircleChevronLeft} />
        </button>
        <div
          className="flex card-container dragscroll"
          ref={buddiesScrollContainer}
        >
          {followingList.slice(0, 15).map((followedUser, index) => {
            return (
              <Link
                key={`follow-user-${followedUser}`}
                className="buddy content-card"
                to={`/user/${encodeURIComponent(
                  followedUser
                )}/year-in-music/${year}/`}
              >
                <div className="small-stat">
                  <div className="value">{followedUser}</div>
                </div>
              </Link>
            );
          })}
        </div>
        <button
          className="btn-icon btn-transparent forward"
          type="button"
          onClick={manualScroll}
        >
          <FontAwesomeIcon icon={faCircleChevronRight} />
        </button>
      </div>
    </div>
  );
}
