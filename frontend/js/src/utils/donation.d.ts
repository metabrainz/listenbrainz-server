type DonationInfo = {
	id: number;
	donated_at: string;
	donation: number;
	currency: "usd" | "eur";
	musicbrainz_id: string;
	is_listenbrainz_user: boolean;
	listenCount: number;
	playlistCount: number;
};

type DonationInfoWithPinnedRecording = DonationInfo & {
	pinnedRecording: PinnedRecording;
};
