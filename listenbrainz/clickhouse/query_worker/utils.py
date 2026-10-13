def describe_load_errors(errors: list[tuple[str, str]]) -> str:
    """Describe the (file, error) of a failed load, which stops at its first failed file."""
    path, error = errors[0]
    return f"parquet file failed to load: {path}: {error}"
