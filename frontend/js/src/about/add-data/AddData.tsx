import * as React from "react";
import { Link } from "react-router-dom";

export default function AddData() {
  return (
    <>
      <h2 className="page-title">Adding your data to Listenbrainz</h2>
      <h3>Submit Listens</h3>
      <p>Submit your listening history to ListenBrainz.</p>
      <h4>Music players</h4>
      <ul>
        <li>
          <em>
            <a href="https://ampcast.app/">Ampcast</a>
          </em>
          , a player, scrobbler and visualiser for personal media servers and
          streaming services
        </li>
        <li>
          <em>
            <a href="https://audacious-media-player.org/">Audacious</a>
          </em>
          , a cross-platform open source audio player:{" "}
          <a href="https://codeberg.org/punkscience/clscrobble">
            <code>clscrobble</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://github.com/ciderapp">Cider</a>
          </em>
          , a cross-platform Apple Music player:{" "}
          <a href="https://marketplace.cider.sh/plugins/10">
            <code>plugin</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://cmus.github.io/">cmus</a>
          </em>
          , a console-based music player for Unix-like operating systems:{" "}
          <a href="https://github.com/vjeranc/cmus-status-scrobbler">
            <code>cmus-status-scrobbler</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://www.foobar2000.org/">Foobar2000</a>
          </em>
          , full-fledged audio player for Windows:{" "}
          <a href="https://github.com/phw/foo_listenbrainz2">
            <code>foo_listenbrainz2</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://wiki.gnome.org/Apps/Lollypop">Lollypop</a>
          </em>
          , a modern music player for GNOME
        </li>
        <li>
          <em>
            <a href="https://longplay.app/">Longplay</a>
          </em>
          , an album-based music player for iOS
        </li>
        <li>
          <em>
            <a href="https://www.musicpd.org/">mpd</a>
          </em>
          , cross-platform server-side application for playing music:{" "}
          <a href="https://codeberg.org/elomatreb/listenbrainz-mpd">
            <code>listenbrainz-mpd</code>
          </a>
          ,{" "}
          <a href="https://github.com/kori/wylt">
            <code>wylt</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://getmusicbee.com/">MusicBee</a>
          </em>
          , a music manager and player for Windows:{" "}
          <a href="https://github.com/karaluh/ScrobblerBrainz">
            <code>ScrobblerBrainz plugin</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://docs.ruuda.nl/musium/listenbrainz/">Musium</a>
          </em>
          , an album-centered music player
        </li>
        <li>
          <em>
            <a href="https://powerampapp.com/">Poweramp</a>
          </em>
          , a music player for Android:{" "}
          <a href="https://github.com/StratusFearMe21/listenbrainz-poweramp">
            <code>plugin</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://quodlibet.readthedocs.io/">Quod Libet</a>
          </em>
          , a cross-platform audio player
        </li>
        <li>
          <em>
            <a href="https://wiki.gnome.org/Apps/Rhythmbox/">Rhythmbox</a>
          </em>
          , a music playing application for GNOME
        </li>
        <li>
          <em>
            <a href="https://www.strawberrymusicplayer.org/">Strawberry</a>
          </em>
          , a cross-platform music player
        </li>
        <li>
          <em>
            <a href="https://tauonmusicbox.rocks/">Tauon Music Box</a>
          </em>
          , a music player for Linux, Arch Linux, and Windows
        </li>
        <li>
          <em>
            <a href="https://github.com/Mastermindzh/tidal-hifi">TIDAL Hi-Fi</a>
          </em>
          , the web version of Tidal running in electron with Hi-Fi (High & Max)
          support
        </li>
        <li>
          <em>
            <a href="https://tidal.com/">TIDAL</a>
          </em>
          , a cross-platform music player and streaming service:{" "}
          <a href="https://github.com/uwu/neptune">
            <code>neptune client mod</code>
          </a>
          +{" "}
          <a href="https://github.com/Inrixia/neptune-plugins?tab=readme-ov-file#listenbrainz">
            <code>ListenBrainz plugin</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://www.videolan.org/vlc/">VLC</a>
          </em>
          , cross-platform multimedia player:{" "}
          <a href="https://github.com/amCap1712/vlc-listenbrainz-plugin">
            <code>VLC Listenbrainz plugin</code>
          </a>
        </li>
      </ul>

      <h4>Standalone programs/streaming servers</h4>
      <ul>
        <li>
          <em>
            <a href="https://github.com/airsonic-advanced/airsonic-advanced">
              Airsonic-Advanced
            </a>
          </em>
          , a free, web-based media streamer
        </li>
        <li>
          <em>
            <a href="https://github.com/PKBeam/AMWin-RP">AMWin-RP</a>
          </em>
          , a Discord Rich Presence client for Apple Music&apos;s native Windows
          app
        </li>
        <li>
          <em>
            <a href="https://github.com/golgote/applescript-listenbrainz">
              applescript-listenbrainz
            </a>
          </em>
          , an applescript service to submit Apple Music listens
        </li>
        <li>
          <em>
            <a href="https://github.com/vvdleun/audiostreamerscrobbler">
              AudioStreamerScrobbler
            </a>
          </em>
          , submit listens from hardware audiostreamers (Bluesound/BluOS,
          MusicCast, HEOS)
        </li>
        <li>
          <em>
            <a href="https://github.com/simonxciv/eavesdrop.fm">Eavesdrop.FM</a>
          </em>
          , submits Plex music listening data to ListenBrainz
        </li>
        <li>
          <em>
            <a href="https://docs.funkwhale.audio/users/builtinplugins.html#listenbrainz-plugin">
              Funkwhale
            </a>
          </em>
          , a decentralized music sharing and listening platform
        </li>
        <li>
          <em>
            <a href="https://github.com/sentriz/gonic">gonic</a>
          </em>
          , a free software Subsonic-compatible music server
        </li>
        <li>
          <em>
            <a href="https://www.home-assistant.io/">Home Assistant</a>
          </em>
          , open source home automation, ListenBrainz support via Music
          Assistant:{" "}
          <a href="https://www.music-assistant.io/plugins/listenbrainz_scrobble/">
            <code>Listenbrainz Scrobbler</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://jellyfin.org/">Jellyfin</a>
          </em>
          , a free software media streaming system:{" "}
          <a href="https://github.com/lyarenei/jellyfin-plugin-listenbrainz">
            <code>jellyfin-plugin-listenbrainz</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://kodi.tv/">Kodi</a>
          </em>
          , a free and open source media center:{" "}
          <a href="https://kodi.tv/addons/matrix/service.listenbrainz">
            <code>ListenBrainz add-on</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://mopidy.com/">Mopidy</a>
          </em>
          , an extensible music player written in Python:{" "}
          <a href="https://github.com/suaviloquence/mopidy-listenbrainz">
            <code>Mopidy-Listenbrainz extension</code>
          </a>
        </li>
        <li>
          <em>
            <a href="https://github.com/mariusor/mpris-scrobbler">
              mpris-scrobbler
            </a>
          </em>
          , a minimalistic unix scrobbler for MPRIS enabled players
        </li>
        <li>
          <em>
            <a href="https://github.com/FoxxMD/multi-scrobbler">
              Multi-scrobbler
            </a>
          </em>
          , a powerful javascript server application for all platforms, with
          support for many sources
        </li>
        <li>
          <em>
            <a href="https://www.navidrome.org/">Navidrome</a>
          </em>
          , a free software music server compatible with Subsonic/Airsonic
        </li>
        <li>
          <em>
            <a href="https://github.com/Atelier-Shiori/OngakuKiroku">
              OngakuKiroku
            </a>
          </em>
          , a ListenBrainz submitter for Swinsian and Music.app on macOS devices
        </li>
        <li>
          <em>
            <a href="https://github.com/InputUsername/rescrobbled">
              Rescrobbled
            </a>
          </em>
          , a universal Linux scrobbler for MPRIS enabled players
        </li>
        <li>
          <em>
            <a href="https://scrobblerad.io/">ScrobbleRadio</a>
          </em>
          , a streaming radio player and listen submitter for a curated list of
          global radio stations
        </li>
        <li>
          <em>
            <a href="https://www.smashbits.nl/smashtunes/">SmashTunes</a>
          </em>
          , a Mac menu bar utility for displaying the current track, submits
          Apple Music and Spotify listens
        </li>
      </ul>

      <h4>Browser extensions</h4>
      <ul>
        <li>
          <em>
            <a href="https://add0n.com/lastfm-scrobbler.html">
              Last.fm Scrobbler
            </a>
          </em>
          , an extension for Firefox and Chrome
        </li>
        <li>
          <em>
            <a href="https://web-scrobbler.com/">Web Scrobbler</a>
          </em>
          , an extension for Firefox and Chrome/Chromium-based browsers
        </li>
      </ul>

      <h4>Mobile devices</h4>
      <ul>
        <li>
          <em>
            <a href="https://play.google.com/store/apps/details?id=org.listenbrainz.android">
              The official ListenBrainz app
            </a>
          </em>
          , for Android devices
        </li>
        <li>
          <em>
            <a href="https://play.google.com/store/apps/details?id=com.arn.scrobble">
              Pano Scrobbler
            </a>
          </em>
          , a scrobbling application for Android Devices
        </li>
      </ul>

      <h4>Scripts</h4>
      <ul>
        <li>
          <em>
            <a href="https://github.com/UnviableFriend/phooks">phooks</a>
          </em>
          , a python script that submits local Plex listens using web hooks and
          file lookups
        </li>
        <li>
          <em>
            <a href="https://github.com/defvs/ytm-extractor">ytm-extractor</a>
          </em>
          , a Kotlin (Java) script to submit your YouTube Music watch history to
          Listenbrainz
        </li>
        <li>
          <em>
            <a href="https://gist.github.com/fuddl/e17aa687df6ac1c7cbee5650ccfbc889">
              YTMusic2listenbrainz.py
            </a>
          </em>
          , a Python script to submit your YouTube Music watch history to
          Listenbrainz
        </li>
      </ul>

      <h3>Submit from Spotify and Last.fm</h3>
      <p>Automatically submit your Spotify or Last.fm listens.</p>
      <p>
        Submitting the same listens from two different sources, such as Last.FM
        and Spotify, may cause duplicates in your listen history. When you opt
        into automatic Spotify submissions you may notice duplicates for your
        last 50 Spotify listens.
      </p>
      <ul>
        <li>
          <em>
            <Link to="/settings/music-services/details/">
              Connect your Spotify or Last.fm account to ListenBrainz
            </Link>
          </em>
        </li>
      </ul>

      <h3>Playlist management</h3>
      <p>
        Submit and store playlists, or generate playlists locally using
        ListenBrainz data
      </p>
      <ul>
        <li>
          <em>
            <a href="https://github.com/Serene-Arc/listenbrainz-playlist-uploader">
              listenbrainz-playlist-uploader
            </a>
          </em>
          , a CLI tool for submitting local M3U playlists to ListenBrainz, as
          well as submitting feedback on tracks
        </li>
        <li>
          <em>
            <a href="https://github.com/regorxxx/ListenBrainz-SMP">
              ListenBrainz-SMP
            </a>
          </em>
          , a Foobar2000 plugin for submitting and retrieving playlists from
          ListenBrainz (+ Spotify). Can retrieve recommendations and submit
          track feedback.
        </li>
        <li>
          <em>
            <a href="https://github.com/regorxxx/Playlist-Manager-SMP">
              Playlist-Manager-SMP
            </a>
          </em>
          , a{" "}
          <em>
            <a href="https://www.foobar2000.org/">Foobar2000</a>
          </em>{" "}
          plugin for syncing local playlists with ListenBrainz (+ Spotify).
          Tracks playlists changes and resolves tracks with local content and
          YouTube links.
        </li>
        <li>
          <em>
            <a href="https://codeberg.org/scaglio/listenbrainz-scrobbler">
              ListenBrainz macOS Scrobbler for Music.app
            </a>
          </em>
          , a macOS Bash script to submit Music.app listens to ListenBrainz
        </li>
        <li>
          <em>
            <a href="https://yogo9.github.io/listenbrainz-recent-listens-to-playlist/">
              ListenBrainz Playlist Tool
            </a>
          </em>{" "}
          <em>
            (
            <a href="https://github.com/YoGo9/listenbrainz-recent-listens-to-playlist">
              Github
            </a>
            )
          </em>
          , a standalone tool to select recent listens from a ListenBrainz
          account and add them to a ListenBrainz playlist.
        </li>
      </ul>

      <h3>Other tools</h3>
      <p>
        Other useful community-made tools to interact with your ListenBrainz
        account
      </p>
      <ul>
        <li>
          <em>
            <a href="https://github.com/coopw1/BrainzBot">BrainzBot</a>
          </em>
          , a Discord bot that can be user-run or added to your server. Showcase
          what you&apos;re listening to, share charts, album grids, tag clouds,
          and more.
        </li>
        <li>
          <em>
            <a href="https://github.com/regorxxx/Wrapped-SMP">Wrapped-SMP</a>
          </em>
          , a Foobar2000 plugin that creates listening reports, similar to
          Spotify&apos;s annual report. Can utilize ListenBrainz
          recommendations.
        </li>
      </ul>

      <h3>For advanced users</h3>
      <p>
        Developers are able to submit their listens to Listenbrainz using the
        Listenbrainz API. Information on how to do this can be found in the{" "}
        <a href="https://listenbrainz.readthedocs.io">API docs</a>.
      </p>
    </>
  );
}
