from listenbrainz.troi.spark import remove_old_playlists, get_user_details, batch_process_playlists

USERS_PER_BATCH = 25
NUMBER_OF_OLD_YIM_PLAYLISTS_TO_KEEP = 1


def exclude_playlists_from_deleted_users(slug, year, jam_name, description, all_playlists):
    """ Remove playlists for users who have deleted their accounts. Also, add more metadata to remaining playlists """
    user_ids = [p["user_id"] for p in all_playlists]
    user_details = get_user_details(slug, user_ids)

    # after removing playlists for users who have been deleted but their
    # data has completely not been removed from spark cluster yet
    playlists = []
    playlists_to_export = []
    for playlist in all_playlists:
        user_id = playlist["user_id"]
        if user_id not in user_details:
            continue

        user = user_details[user_id]
        if user["username"] not in ["rob", "lucifer", "mr_monkey", "aerozol"]:
            continue

        similar_users = ""
        if playlist.get("similar_users"):
            usernames = []
            for other_user_id in playlist["similar_users"]:
                if other_user_id in user_details:
                    other_username = user_details[other_user_id]["username"]
                    usernames.append(other_username)
            similar_users = ", ".join(usernames)

        playlist["name"] = jam_name.format(year=year, user=user["username"])
        playlist["description"] = description.format(year=year, user=user["username"], similar_users=similar_users)
        playlist["existing_url"] = user["existing_url"]
        playlist["additional_metadata"] = {"algorithm_metadata": {"source_patch": slug}}

        playlists.append(playlist)
        if user["export_to_spotify"]:
            playlists_to_export.append(playlist)

    return playlists, playlists_to_export


def process_yim_playlists(slug, year, playlists):
    """ Generate playlists for a batch of users """
    if slug == "top-discoveries":
        playlist_name = "Top Discoveries of {year} for {user}"
        playlist_description = """
            <p>
                This playlist contains the top tracks for {user} that were first listened to in {year}.
            </p>
            <p>
                For more information on how this playlist is generated, please see our
                <a href="https://musicbrainz.org/doc/YIM{year}Playlists">Year in Music {year} Playlists</a> page.
            </p>
        """
    elif slug == "top-missed-recordings":
        playlist_name = "Top Missed Recordings of {year} for {user}"
        playlist_description = """
            <p>
                This playlist features recordings that were listened to by users similar to {user} in {year}.
                It is a discovery playlist that aims to introduce you to new music that other similar users
                enjoy. It may require more active listening and may contain tracks that are not to your taste.
            </p>
            <p>
                The users similar to you who contributed to this playlist: {similar_users}.
            </p>
            <p>
                For more information on how this playlist is generated, please see our
                <a href="https://musicbrainz.org/doc/YIM{year}Playlists">Year in Music {year} Playlists</a> page.
            </p>
        """
    else:
        return
    playlist_slug = f"{slug}-of-{year}"

    all_playlists, playlists_to_export = exclude_playlists_from_deleted_users(
        playlist_slug,
        year,
        playlist_name,
        playlist_description,
        playlists
    )
    batch_process_playlists(all_playlists, playlists_to_export)


def process_yim_playlists_end(slug, year):
    remove_old_playlists(f"{slug}-of-{year}", NUMBER_OF_OLD_YIM_PLAYLISTS_TO_KEEP)
