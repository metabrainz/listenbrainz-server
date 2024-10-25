import * as React from "react";
import { Link } from "react-router-dom";

export default function About() {
  return (
    <>
      <h2 className="page-title">Goals</h2>
      <p>The ListenBrainz project has a number of goals:</p>
      <ol>
        <li>
          <b>A public store of your listen history.</b> We feel that a listen
          history has a tremendous amount of personal value and in aggregate has
          a huge amount of value for developers who wish to create better music
          technologies, like recommendation systems.
        </li>
        <li>
          <b>A permanent store of your listen history.</b> MetaBrainz, the
          non-profit that runs <a href="https://musicbrainz.org">MusicBrainz</a>{" "}
          and ListenBrainz has a long history of curating and making data
          available to the public in a useful and meaningful manner. We promise
          to safeguard your listen history permanently.
        </li>
        <li>
          <b>
            To make data dumps of this listen history available for download.
          </b>{" "}
          We want everyone who is interested in this data to have access to the
          data and to use it in any manner they wish.
        </li>
        <li>
          <b>To share listen histories in a distributed fashion.</b> We plan to
          allow anyone to connect to ListenBrainz and to tap into a live feed of
          listen data as we receive it. We hope that Last.fm will work with us
          to make an interconnection with Last.fm possible. We welcome anyone
          scrobbling to us and we plan to share the listens shared with us to
          anyone else who wants them. We envision smaller music communities with
          a specific focus to install their own ListenBrainz server to collect
          listen data for their specific focus. We hope that these smaller
          communities will also share their data in the same manner in which we
          share our data.
        </li>
      </ol>
      <h3>Anti-goals</h3>
      <p>
        The project also has a number of anti-goals (things it doesn&apos;t try
        to be):
      </p>
      <ol>
        <li>
          <b>A store for people&apos;s private listen history.</b> The point of
          this project is to build a public, shareable store of listen data. As
          we build out our sharing features, building a private listen store
          will become possible, but that is not part of our goals.
        </li>
        <li>
          <b>A closed platform.</b> We aim to make everything open and to
          encourage a community of sharing and participation.
        </li>
      </ol>
      <h2 className="page-title">Roadmap</h2>
      We&apos;ve put together a very rough roadmap for this project:
      <h3>Short term</h3>
      <ul>
        <li>Work to improve and extend the user data graphing features.</li>
      </ul>
      <h3>Medium term</h3>
      <ul>
        <li>
          Start working on an open source recommendation engine using data from
          ListenBrainz, <a href="https://acousticbrainz.org">AcousticBrainz</a>{" "}
          and <a href="https://musicbrainz.org">MusicBrainz</a>.
        </li>
      </ul>
      <h3>Long term</h3>
      <ul>
        <li>
          Total world domination. What other goals are open source projects
          allowed to have?
        </li>
      </ul>
      <br />
      <p>
        If you have any ideas that should be on our roadmap, please{" "}
        <a href="https://metabrainz.org/contact">let us know</a>!
      </p>
      <h2 className="page-title">Contributing to ListenBrainz</h2>
      <h3>Donating</h3>
      <p>
        Listenbrainz is a free open source project that is not run for profit.
        If you would like to help the project out financially, consider{" "}
        <Link to="/donate/">donating</Link> to the MetaBrainz Foundation.
      </p>
      <h3>Developers</h3>
      <p>
        ListenBrainz is in its infancy and we need a lot of help to implement
        more features and to debug the existing features. If you feel like
        helping out and have experience with Python, Postgres and Redis,
        we&apos;d love some help.
      </p>
      <p>
        Have a look at the{" "}
        <a href="https://github.com/metabrainz/listenbrainz-server">
          GitHub repository
        </a>{" "}
        for this project to get started. You may also consider heading to our
        IRC channel #metabrainz on irc.libera.chat and asking people there what
        should be worked on next. Finally, we also have a bug tracker that keeps
        track of our{" "}
        <a href="http://tickets.musicbrainz.org/browse/LB">current issues</a>.
      </p>
    </>
  );
}
