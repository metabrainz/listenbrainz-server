import { faThumbtack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { Link } from "react-router-dom";
import {
  getRecordingMBID,
  getTrackName,
  pinnedRecordingToListen,
} from "../../utils/utils";
import Username from "../../common/Username";

type RecentDonorsCardProps = {
  donors: DonationInfoWithPinnedRecording[];
};

function RecentDonorsCard(props: RecentDonorsCardProps) {
  const { donors } = props;

  if (!donors || donors.length === 0) {
    return null;
  }

  return (
    <>
      <h3 className="text-center" style={{ marginTop: "10px" }}>
        Recent Donors
        <br />
        <small>
          <Link to="/donors/">See all donations</Link>
        </small>
      </h3>
      <div className="similar-users-list">
        {donors &&
          donors.map((donor) => {
            const pinnedRecordingListen = donor.pinnedRecording
              ? pinnedRecordingToListen(donor.pinnedRecording)
              : null;
            return (
              <div key={donor.id} className="recent-donor-card">
                <div>
                  {donor.musicbrainz_id &&
                    (donor.is_listenbrainz_user ? (
                      <Username
                        username={donor.musicbrainz_id}
                        className="user-link"
                      />
                    ) : (
                      <Link
                        to={`https://musicbrainz.org/user/${donor.musicbrainz_id}`}
                        className="user-link"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {donor.musicbrainz_id}
                      </Link>
                    ))}
                  <p>
                    {donor.currency === "usd" ? "$" : "€"}
                    {donor.donation}
                  </p>
                </div>
                {pinnedRecordingListen && (
                  <Link
                    className="donor-pinned-recording btn btn-sm"
                    to={`https://musicbrainz.org/recording/${getRecordingMBID(
                      pinnedRecordingListen
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    tabIndex={0}
                  >
                    <FontAwesomeIcon icon={faThumbtack} />
                    <div className="text">
                      {getTrackName(pinnedRecordingListen)}
                    </div>
                  </Link>
                )}
              </div>
            );
          })}
      </div>
    </>
  );
}

export default RecentDonorsCard;
