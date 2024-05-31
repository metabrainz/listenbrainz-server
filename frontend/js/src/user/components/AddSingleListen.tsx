import React, { useEffect, useState } from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import ListenControl from "../../common/listens/ListenControl";
import { convertDateToUnixTimestamp } from "../../utils/utils";
import ListenCard from "../../common/listens/ListenCard";
import SearchTrackOrMBID from "../../utils/SearchTrackOrMBID";

function getListenFromTrack(
  selectedDate: Date,
  selectedTrackMetadata?: TrackMetadata
): Listen | undefined {
  if (!selectedTrackMetadata) {
    return undefined;
  }

  return {
    listened_at: convertDateToUnixTimestamp(selectedDate),
    track_metadata: {
      ...selectedTrackMetadata,
      additional_info: {
        ...selectedTrackMetadata.additional_info,
        submission_client: "listenbrainz web",
      },
    },
  };
}
interface AddSingleListenProps {
  selectedDate: Date;
  onPayloadChange: (listens: Listen[]) => void;
}

export default function AddSingleListen({
  selectedDate,
  onPayloadChange,
}: AddSingleListenProps) {
  const [selectedTrack, setSelectedTrack] = useState<TrackMetadata>();

  const resetTrackSelection = () => {
    setSelectedTrack(undefined);
  };
  const listenFromSelectedTrack = getListenFromTrack(
    selectedDate,
    selectedTrack
  );

  useEffect(() => {
    if (listenFromSelectedTrack) {
      onPayloadChange([listenFromSelectedTrack]);
    } else {
      onPayloadChange([]);
    }
  }, [listenFromSelectedTrack, onPayloadChange]);

  return (
    <div>
      <SearchTrackOrMBID
        onSelectRecording={(newSelectedTrackMetadata) => {
          setSelectedTrack(newSelectedTrackMetadata);
        }}
      />
      <div className="track-info">
        <div className="content">
          {listenFromSelectedTrack && (
            <ListenCard
              listen={listenFromSelectedTrack}
              showTimestamp={false}
              showUsername={false}
              // eslint-disable-next-line react/jsx-no-useless-fragment
              feedbackComponent={<></>}
              compact
              additionalActions={
                <ListenControl
                  buttonClassName="btn btn-transparent"
                  text=""
                  title="Reset"
                  icon={faTimesCircle}
                  iconSize="lg"
                  action={resetTrackSelection}
                />
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
