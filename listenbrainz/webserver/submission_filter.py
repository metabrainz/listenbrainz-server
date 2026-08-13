"""
Submission filter engine for evaluating user-defined filters against incoming listens.

Each filter has an action ("ignore") and a list of conditions.
All conditions within a filter must match (AND logic) for the filter to trigger.
If any one filter matches, the listen is dropped (OR logic across filters).
"""


def evaluate_condition(track_metadata, condition):
    """Evaluate a single filter condition against listen track_metadata.

    Args:
        track_metadata: the track_metadata dict from the listen payload
        condition: a dict with keys 'field', 'operator', 'value'

    Returns:
        True if the condition matches, False otherwise
    """
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    expected_value = condition.get("value", "")

    actual_value = track_metadata.get(field)

    # if the field doesn't exist in the listen, the condition doesn't match
    if actual_value is None:
        return False

    # case-insensitive comparison
    actual_lower = actual_value.lower()
    expected_lower = expected_value.lower()

    if operator == "eq":
        return actual_lower == expected_lower
    elif operator == "neq":
        return actual_lower != expected_lower
    elif operator == "contains":
        return expected_lower in actual_lower
    else:
        return False


def does_listen_match_filter(listen, submission_filter):
    """Check if a listen matches a single submission filter.

    A filter matches if ALL its conditions match (AND logic).

    Args:
        listen: the validated listen payload dict
        submission_filter: a dict with 'action' and 'conditions' keys

    Returns:
        True if the listen matches the filter (should be dropped), False otherwise
    """
    conditions = submission_filter.get("conditions", [])
    if not conditions:
        return False

    track_metadata = listen.get("track_metadata", {})
    return all(evaluate_condition(track_metadata, condition) for condition in conditions)


def apply_submission_filters(listen, filters):
    """Evaluate all submission filters against a listen.

    A listen is dropped if ANY filter matches (OR logic across filters).

    Args:
        listen: the validated listen payload dict
        filters: a list of filter dicts, each with 'action' and 'conditions'

    Returns:
        True if the listen should be DROPPED, False if it should be kept
    """
    if not filters:
        return False

    return any(
        submission_filter.get("action") == "ignore" and does_listen_match_filter(listen, submission_filter)
        for submission_filter in filters
    )
