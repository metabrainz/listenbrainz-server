import * as React from "react";
import { Link } from "react-router-dom";
import useUserFlairs from "../utils/FlairLoader";

type BaseUsernameProps = {
  username: string;
  hideFlair?: boolean;
  [key: string]: any;
};

type WithLinkProps = BaseUsernameProps & {
  hideLink?: false;
};

type WithElementProps = BaseUsernameProps & {
  hideLink: true;
  elementType: keyof JSX.IntrinsicElements;
};

function Username(props: WithLinkProps | WithElementProps) {
  const {
    username,
    elementType,
    hideFlair = false,
    hideLink = false,
    ...otherProps
  } = props;
  const flairType = useUserFlairs(username);

  if (!hideLink) {
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

  const Element = elementType;
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

export default Username;
