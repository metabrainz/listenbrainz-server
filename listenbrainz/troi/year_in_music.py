from listenbrainz.troi.spark import remove_old_playlists, get_user_details, batch_process_playlists

USERS_PER_BATCH = 25
NUMBER_OF_OLD_YIM_PLAYLISTS_TO_KEEP = 1


def get_similar_usernames_part(user_details, similar_users):
    """ Generate html formatted links to similar users part for top-missed-recordings playlist """
    usernames = []
    for other_user_id in similar_users:
        if other_user_id in user_details:
            other_username = user_details[other_user_id]["username"]
            usernames.append(f'<a href="https://listenbrainz.org/user/{other_username}">{other_username}</a>')
    return ", ".join(usernames)


def exclude_playlists_from_deleted_users(slug, year, jam_name, description, user_details, all_playlists):
    """ Remove playlists for users who have deleted their accounts. Also, add more metadata to remaining playlists """
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
        if slug == "top-missed-recordings":
            similar_users = get_similar_usernames_part(user_details, playlist["similar_users"])

        playlist["name"] = jam_name.format(year=year, user=user["username"])
        playlist["description"] = description.format(year=year, user=user["username"], similar_users=similar_users)
        playlist["existing_url"] = user["existing_url"]
        playlist["additional_metadata"] = {"algorithm_metadata": {"source_patch": f"{slug}-of-{year}"}}

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
        user_ids = [p["user_id"] for p in playlists]
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
        user_ids = set()
        for playlist in playlists:
            user_ids.add(playlist["user_id"])
            user_ids.update(playlist["similar_users"])
        user_ids = list(user_ids)
    else:
        return

    user_details = get_user_details(slug, user_ids)

    all_playlists, playlists_to_export = exclude_playlists_from_deleted_users(
        slug,
        year,
        playlist_name,
        playlist_description,
        user_details,
        playlists
    )
    batch_process_playlists(all_playlists, playlists_to_export)


def process_yim_playlists_end(slug, year):
    remove_old_playlists(f"{slug}-of-{year}", NUMBER_OF_OLD_YIM_PLAYLISTS_TO_KEEP)
