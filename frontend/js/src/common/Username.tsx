import * as React from "react";
import { Link } from "react-router-dom";
import useUserFlairs from "../utils/FlairLoader";

function Username({
  username,
  elementType,
  hideFlair = false,
  showLink = false,
  ...otherProps
}: {
  username: string;
  elementType?: keyof JSX.IntrinsicElements;
  hideFlair?: boolean;
  showLink?: boolean;
  [key: string]: any;
}) {
  const Element = elementType;
  const flairType = useUserFlairs(username);

  if (showLink) {
    return (
      <Link
        to={`/user/${username}/`}
        {...otherProps}
        className={`${otherProps?.className || ""} ${
          !hideFlair ? flairType || "" : ""
        }`}
        title={username}
      >
        {username}
      </Link>
    );
  }
  if (Element) {
    return (
      <Element
        {...otherProps}
        className={`${otherProps?.className || ""} ${
          !hideFlair ? flairType || "" : ""
        }`}
        title={username}
      >
        {username}
      </Element>
    );
  }
  // eslint-disable-next-line react/jsx-no-useless-fragment
  return <>{username}</>;
}

export default Username;
