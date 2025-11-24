import React from "react";
import humanizeDuration from "humanize-duration";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { YearInMusicProps } from "../YearInMusic";

type YIMStatsProps = {
  yearInMusicData: YearInMusicProps["yearInMusicData"];
  userName: string;
};
export default function YIMStats({ yearInMusicData, userName }: YIMStatsProps) {
  const { currentUser } = React.useContext(GlobalAppContext);
  const isCurrentUser = userName === currentUser?.name;
  const yourOrUsersName = isCurrentUser ? "your" : `${userName}'s`;
  if (!yearInMusicData) {
    return null;
  }

  let newArtistsDiscovered: number | string =
    yearInMusicData?.total_new_artists_discovered ?? 0;
  let newArtistsDiscoveredPercentage;
  if (yearInMusicData) {
    newArtistsDiscoveredPercentage = Math.round(
      (yearInMusicData.total_new_artists_discovered /
        yearInMusicData.total_artists_count) *
        100
    );
  }
  if (!Number.isNaN(newArtistsDiscoveredPercentage)) {
    newArtistsDiscovered = `${newArtistsDiscoveredPercentage}%`;
  }

  return (
    <div className="small-stats">
      {yearInMusicData.total_listen_count && (
        <div className="small-stat text-center">
          <div className="value">{yearInMusicData.total_listen_count}</div>
          <span>songs graced {yourOrUsersName} ears</span>
        </div>
      )}
      {yearInMusicData.total_listening_time && (
        <div className="small-stat text-center">
          <div className="value">
            {humanizeDuration(yearInMusicData.total_listening_time * 1000, {
              largest: 1,
              round: true,
            })}
          </div>
          <span>of music (at least!)</span>
        </div>
      )}
      {yearInMusicData.total_release_groups_count && (
        <div className="small-stat text-center">
          <div className="value">
            {yearInMusicData.total_release_groups_count}
          </div>
          <span>albums in total</span>
        </div>
      )}
      {yearInMusicData.total_artists_count && (
        <div className="small-stat text-center">
          <div className="value">{yearInMusicData.total_artists_count}</div>
          <span>artists got {yourOrUsersName} attention</span>
        </div>
      )}
      {newArtistsDiscovered && (
        <div className="small-stat text-center">
          <div className="value">{newArtistsDiscovered}</div>
          <span>new artists discovered</span>
        </div>
      )}
      {yearInMusicData.day_of_week && (
        <div className="small-stat text-center">
          <div className="value">{yearInMusicData.day_of_week}</div>
          <span>was {yourOrUsersName} music day</span>
        </div>
      )}
    </div>
  );
}
