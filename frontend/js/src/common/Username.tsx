import * as React from "react";
import { Link } from "react-router-dom";
import useUserFlairs from "../utils/FlairLoader";

interface BaseUsernameProps extends React.HTMLAttributes<HTMLElement> {
  username: string;
  hideFlair?: boolean;
}

type WithLinkProps = BaseUsernameProps & {
  hideLink?: false;
  elementType?: undefined;
};

type WithElementProps = BaseUsernameProps & {
  hideLink: true;
  elementType: keyof HTMLElementTagNameMap;
};

function Username(props: WithLinkProps | WithElementProps) {
  const {
    username,
    elementType = "div",
    hideFlair = false,
    hideLink = false,
    ...otherProps
  } = props;
  const flairType = useUserFlairs(username);
  const cssClasses = `${otherProps?.className || ""} ${
    !hideFlair ? `flair ${flairType || ""}` : ""
  }`;
  const htmlContent = username;

  if (!hideLink) {
    return (
      <Link
        to={`/user/${username}/`}
        {...otherProps}
        className={cssClasses}
        title={username}
      >
        {htmlContent}
      </Link>
    );
  }

  return React.createElement(
    elementType,
    {
      ...otherProps,
      className: cssClasses,
      title: username,
    },
    htmlContent
  );
}

export default Username;
