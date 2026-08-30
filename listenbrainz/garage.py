"""MinIO client for Garage's S3-compatible API."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import urllib3
from flask import current_app
from minio import Minio
from minio.error import S3Error

# minio's default pool only allows 10 connections, an export download holds one for the entire
# duration of the transfer so a handful of concurrent downloads would exhaust it.
CONNECTION_POOL_SIZE = 50
CONNECTION_TIMEOUT = timedelta(minutes=5).seconds


class GarageConfigurationError(ValueError):
    """Raised when the Garage client configuration is incomplete or invalid."""


def create_garage_client(config: Mapping[str, Any]) -> Minio:
    """Create a MinIO client configured for Garage."""
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

    # same as the client minio creates by default, except for the larger pool. urllib3 verifies
    # certificates against the system trust store by default so the ca bundle is left to it.
    http_client = urllib3.PoolManager(
        timeout=urllib3.util.Timeout(connect=CONNECTION_TIMEOUT, read=CONNECTION_TIMEOUT),
        maxsize=CONNECTION_POOL_SIZE,
        cert_reqs="CERT_REQUIRED",
        retries=urllib3.Retry(total=5, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]),
    )

    return Minio(
        endpoint,
        access_key=str(config["GARAGE_ACCESS_KEY"]),
        secret_key=str(config["GARAGE_SECRET_KEY"]),
        secure=secure,
        region=str(config.get("GARAGE_REGION", "garage")),
        http_client=http_client,
    )


def get_garage_client() -> Minio:
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


def ensure_bucket(client: Minio, bucket: str):
    """Create the given bucket if it does not exist yet.

    Buckets are created by ops in production, this only matters for development
    setups where the bucket has not been provisioned yet.
    """
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except S3Error as e:
        # another worker may have created the bucket in the meantime
        if e.code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise
