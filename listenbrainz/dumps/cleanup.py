import os
import re
import shutil
import sys
from dataclasses import dataclass

NUMBER_OF_FULL_DUMPS_TO_KEEP = 2
NUMBER_OF_DB_DUMPS_TO_KEEP = 2
NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP = 30
NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP = 2
NUMBER_OF_CANONICAL_DUMPS_TO_KEEP = 2
NUMBER_OF_SAMPLE_DUMPS_TO_KEEP = 2


@dataclass(frozen=True)
class DumpKind:
    """ The retention policy for one type of dump.

    The pattern must match a complete dump directory name and capture, in order,
    the numeric fields which sort dumps of this kind from oldest to newest.
    """
    name: str
    pattern: re.Pattern
    keep: int

    def sort_key(self, dump_name):
        return tuple(int(field) for field in self.pattern.fullmatch(dump_name).groups())


DUMP_KINDS = (
    DumpKind(
        'full',
        re.compile(r'listenbrainz-dump-(\d+)-\d{8}-\d{6}-full'),
        NUMBER_OF_FULL_DUMPS_TO_KEEP,
    ),
    DumpKind(
        'db',
        re.compile(r'listenbrainz-dump-(\d+)-\d{8}-\d{6}-db'),
        NUMBER_OF_DB_DUMPS_TO_KEEP,
    ),
    DumpKind(
        'incremental',
        re.compile(r'listenbrainz-dump-(\d+)-\d{8}-\d{6}-incremental'),
        NUMBER_OF_INCREMENTAL_DUMPS_TO_KEEP,
    ),
    DumpKind(
        'feedback',
        re.compile(r'listenbrainz-feedback-(\d{8})-(\d{6})-full'),
        NUMBER_OF_FEEDBACK_DUMPS_TO_KEEP,
    ),
    DumpKind(
        'sample',
        re.compile(r'listenbrainz-sample-(\d{8})-(\d{6})-full'),
        NUMBER_OF_SAMPLE_DUMPS_TO_KEEP,
    ),
    DumpKind(
        'canonical',
        re.compile(r'musicbrainz-canonical-dump-(\d{8})-(\d{6})'),
        NUMBER_OF_CANONICAL_DUMPS_TO_KEEP,
    ),
)


def parse_keep_overrides(overrides):
    """ Parse `KIND=COUNT` retention overrides into a dict.

    Args:
        overrides (Iterable[str]): overrides in `KIND=COUNT` form, e.g. `full=0`

    Raises:
        ValueError: if a kind is unknown or a count is not a non-negative integer
    """
    known_kinds = {kind.name for kind in DUMP_KINDS}
    parsed = {}
    for override in overrides:
        kind, separator, count = override.partition('=')
        if not separator or kind not in known_kinds or not count.isdigit():
            raise ValueError(
                f"invalid retention override '{override}', expected KIND=COUNT where KIND is one of "
                f"{', '.join(sorted(known_kinds))} and COUNT is a non-negative integer"
            )
        parsed[kind] = int(count)
    return parsed


def select_expired_dumps(dump_names, keep_overrides=None):
    """ Select the dumps which have fallen outside their kind's retention window.

    This is the single definition of the retention policy. It works on names
    alone so that the same policy can be applied to a local directory and to a
    listing of the remote FTP host. Names which do not belong to a known dump
    kind are ignored.

    Args:
        dump_names (Iterable[str]): dump directory names
        keep_overrides (dict): number of dumps to keep, by kind name, overriding the defaults

    Returns:
        list[str]: the names of the dumps which should be deleted, newest first
    """
    keep_overrides = keep_overrides or {}
    dump_names = list(dump_names)
    expired = []

    for kind in DUMP_KINDS:
        keep = keep_overrides.get(kind.name, kind.keep)
        dumps = sorted(
            (name for name in dump_names if kind.pattern.fullmatch(name)),
            key=kind.sort_key,
            reverse=True,
        )
        if not dumps:
            print(f'No {kind.name} dumps present!', file=sys.stderr)
            continue

        for name in dumps[:keep]:
            print(f'Keeping {name}...', file=sys.stderr)
        expired.extend(dumps[keep:])

    return expired


def _cleanup_dumps(location, keep_overrides=None):
    """ Delete the dumps in a local directory which have fallen outside their kind's retention window.

    Args:
        location (str): the dir which needs to be cleaned up
        keep_overrides (dict): number of dumps to keep, by kind name, overriding the defaults

    Returns:
        (int, int): the number of entries remaining in the directory, the number of dumps deleted
    """
    if not os.path.exists(location):
        print(f'Location {location} does not exist!', file=sys.stderr)
        return 0, 0

    entries = os.listdir(location)
    expired = select_expired_dumps(entries, keep_overrides)
    for name in expired:
        print(f'Removing {name}...', file=sys.stderr)
        shutil.rmtree(os.path.join(location, name))

    print(f'Deleted {len(expired)} old exports from {location}!', file=sys.stderr)
    return len(entries) - len(expired), len(expired)
