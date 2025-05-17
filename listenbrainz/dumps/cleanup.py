import os
import re
import shutil

NUMBER_OF_FULL_DUMPS_TO_KEEP = 2
NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP = 30
NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP = 2
NUMBER_OF_CANONICAL_DUMPS_TO_KEEP = 2


def _cleanup_dumps(location):
    """ Delete old dumps while keeping the latest two dumps in the specified directory

    Args:
        location (str): the dir which needs to be cleaned up

    Returns:
        (int, int): the number of dumps remaining, the number of dumps deleted
    """
    if not os.path.exists(location):
        print(f'Location {location} does not exist!')
        return

    # Clean up full dumps
    full_dump_re = re.compile('listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-full')
    dump_files = [x for x in os.listdir(location) if full_dump_re.match(x)]
    full_dumps = [x for x in sorted(dump_files, key=get_dump_id, reverse=True)]
    if not full_dumps:
        print('No full dumps present in specified directory!')
    else:
        remove_dumps(location, full_dumps, NUMBER_OF_FULL_DUMPS_TO_KEEP)

    # Clean up incremental dumps
    incremental_dump_re = re.compile(
        'listenbrainz-dump-[0-9]*-[0-9]*-[0-9]*-incremental')
    dump_files = [x for x in os.listdir(
        location) if incremental_dump_re.match(x)]
    incremental_dumps = [x for x in sorted(
        dump_files, key=get_dump_id, reverse=True)]
    if not incremental_dumps:
        print('No incremental dumps present in specified directory!')
    else:
        remove_dumps(location, incremental_dumps,
                     NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP)

    # Clean up spark / feedback dumps
    spark_dump_re = re.compile(
        'listenbrainz-feedback-[0-9]*-[0-9]*-full')
    dump_files = [x for x in os.listdir(
        location) if spark_dump_re.match(x)]
    spark_dumps = [x for x in sorted(
        dump_files, key=get_dump_ts, reverse=True)]
    if not spark_dumps:
        print('No spark feedback dumps present in specified directory!')
    else:
        remove_dumps(location, spark_dumps,
                     NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP)

    # Clean up canonical dumps
    mbcanonical_dump_re = re.compile(
        'musicbrainz-canonical-dump-[0-9]*-[0-9]*')
    dump_files = [x for x in os.listdir(
        location) if mbcanonical_dump_re.match(x)]
    mbcanonical_dumps = [x for x in sorted(
        dump_files, key=lambda dump_name: dump_name.split('-')[3] + dump_name.split('-')[4], reverse=True)]
    if not mbcanonical_dumps:
        print('No canonical dumps present in specified directory!')
    else:
        remove_dumps(location, mbcanonical_dumps,
                     NUMBER_OF_CANONICAL_DUMPS_TO_KEEP)


def remove_dumps(location, dumps, remaining_count):
    keep = dumps[0:remaining_count]
    keep_count = 0
    for dump in keep:
        print('Keeping %s...' % dump)
        keep_count += 1

    remove = dumps[remaining_count:]
    remove_count = 0
    for dump in remove:
        print('Removing %s...' % dump)
        shutil.rmtree(os.path.join(location, dump))
        remove_count += 1

    print('Deleted %d old exports, kept %d exports!' %
          (remove_count, keep_count))
    return keep_count, remove_count


def get_dump_id(dump_name):
    return int(dump_name.split('-')[2])


def get_dump_ts(dump_name):
    return dump_name.split('-')[2] + dump_name.split('-')[3]
