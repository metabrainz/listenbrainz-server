"""boto3 client for Garage's S3-compatible API."""

from collections.abc import Iterable, Mapping
from datetime import timedelta
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError
from flask import current_app

# botocore's default pool only allows 10 connections, an export download holds one for the entire
# duration of the transfer so a handful of concurrent downloads would exhaust it.
CONNECTION_POOL_SIZE = 50
CONNECTION_TIMEOUT = timedelta(minutes=5).seconds
# maximum number of keys a single DeleteObjects request accepts
DELETE_BATCH_SIZE = 1000


class GarageConfigurationError(ValueError):
    """Raised when the Garage client configuration is incomplete or invalid."""


def get_error_code(error: ClientError) -> str:
    """Get the S3 error code of the given error, an empty string if it has none."""
    return error.response.get("Error", {}).get("Code", "")


def create_garage_client(config: Mapping[str, Any]) -> BaseClient:
    """Create a boto3 S3 client configured for Garage."""
    required = ("GARAGE_ENDPOINT", "GARAGE_ACCESS_KEY", "GARAGE_SECRET_KEY")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise GarageConfigurationError(
            f"Missing Garage configuration: {', '.join(missing)}"
        )

    endpoint = str(config["GARAGE_ENDPOINT"])
    if "://" in endpoint:
        raise GarageConfigurationError(
            "GARAGE_ENDPOINT must be host:port without a URL scheme"
        )

    secure = config.get("GARAGE_SECURE", False)
    if not isinstance(secure, bool):
        raise GarageConfigurationError("GARAGE_SECURE must be a boolean")

    client_config = Config(
        region_name=str(config.get("GARAGE_REGION", "garage")),
        signature_version="s3v4",
        # garage serves one host, virtual hosted style buckets would resolve to a name that
        # does not exist
        s3={"addressing_style": "path"},
        max_pool_connections=CONNECTION_POOL_SIZE,
        connect_timeout=CONNECTION_TIMEOUT,
        read_timeout=CONNECTION_TIMEOUT,
        retries={"max_attempts": 5, "mode": "standard"},
        # garage is not S3, only compute the checksums the operations that require them need
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )

    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
        aws_access_key_id=str(config["GARAGE_ACCESS_KEY"]),
        aws_secret_access_key=str(config["GARAGE_SECRET_KEY"]),
        config=client_config,
    )


def get_garage_client() -> BaseClient:
    """Get the Garage client for the current app, creating it on first use."""
    client = current_app.extensions.get("garage")
    if client is None:
        client = current_app.extensions["garage"] = create_garage_client(current_app.config)
    return client


def get_user_data_export_bucket() -> str:
    """Get the name of the bucket user data exports are stored in."""
    bucket = current_app.config.get("GARAGE_USER_DATA_EXPORT_BUCKET")
    if not bucket:
        raise GarageConfigurationError("Missing Garage configuration: GARAGE_USER_DATA_EXPORT_BUCKET")
    return bucket


def get_user_data_import_bucket() -> str:
    """Get the name of the bucket the files uploaded for user data imports are stored in."""
    bucket = current_app.config.get("GARAGE_USER_DATA_IMPORT_BUCKET")
    if not bucket:
        raise GarageConfigurationError("Missing Garage configuration: GARAGE_USER_DATA_IMPORT_BUCKET")
    return bucket


def bucket_exists(client: BaseClient, bucket: str) -> bool:
    """Check whether the given bucket exists and is accessible with our credentials."""
    try:
        client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        # a HEAD response has no body to carry the error code in, botocore reports the status
        if get_error_code(e) in ("404", "NoSuchBucket"):
            return False
        raise


def ensure_bucket(client: BaseClient, bucket: str):
    """Create the given bucket if it does not exist yet.

    Buckets are created by ops in production, this only matters for development
    setups where the bucket has not been provisioned yet.
    """
    try:
        if not bucket_exists(client, bucket):
            client.create_bucket(Bucket=bucket)
    except ClientError as e:
        # another worker may have created the bucket in the meantime
        if get_error_code(e) not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def list_object_names(client: BaseClient, bucket: str) -> list[str]:
    """List the names of all the objects in the given bucket."""
    names = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        names.extend(obj["Key"] for obj in page.get("Contents", []))
    return names


def delete_objects(client: BaseClient, bucket: str, object_names: Iterable[str]) -> list[dict]:
    """Delete the given objects from the bucket, returning the errors the deletions failed with.

    A DeleteObjects request only accepts a limited number of keys, so the deletion is split
    into batches. Errors do not raise, S3 reports them per object in the response.
    """
    names = list(object_names)
    errors = []
    for index in range(0, len(names), DELETE_BATCH_SIZE):
        batch = names[index:index + DELETE_BATCH_SIZE]
        response = client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": name} for name in batch], "Quiet": True},
        )
        errors.extend(response.get("Errors", []))
    return errors
