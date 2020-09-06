/*
 * listenbrainz-server - Server for the ListenBrainz project.
 *
 * Copyright (C) 2020 Param Singh <iliekcomputers@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */

import * as React from "react";
import * as ReactDOM from "react-dom";

const FollowButton = (currentUser: any) => {
  // this renders the logged-in user's name right now, should render the name of the user whose
  // profile it is
  return (
    <>
      <h2 className="page-title">{currentUser.name}</h2>
      <span>Yo yo, pammu</span>
    </>
  );
};

document.addEventListener("DOMContentLoaded", () => {
  const domContainer = document.querySelector("#follow-controls-container");

  const propsElement = document.getElementById("react-props");
  const reactProps = JSON.parse(propsElement!.innerHTML);
  const { current_user } = reactProps;
  ReactDOM.render(<FollowButton currentUser={current_user} />, domContainer);
});
