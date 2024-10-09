import { faThumbtack } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { Link } from "react-router-dom";
import {
  getRecordingMBID,
  getTrackName,
  pinnedRecordingToListen,
} from "../../utils/utils";

type RecentDonorsCardProps = {
  donors: DonationInfoWithPinnedRecording[];
};

function RecentDonorsCard(props: RecentDonorsCardProps) {
  const { donors } = props;

  return (
    <>
      <h3 className="text-center" style={{ marginTop: "10px" }}>
        Recent Donors
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
                      <Link
                        to={`/user/${donor.musicbrainz_id}`}
                        className="user-link"
                      >
                        {donor.musicbrainz_id}
                      </Link>
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
