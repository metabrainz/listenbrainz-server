"""Persistent query jobs, claimed like background tasks."""

import orjson
from sqlalchemy import text

from listenbrainz.webserver import db_conn


CLAIM_TIMEOUT_HOURS = 6


def add_job(query, params):
    db_conn.execute(text("INSERT INTO clickhouse_query_jobs (query, params) VALUES (:query, CAST(:params AS JSONB))"),
                    {"query": query, "params": orjson.dumps(params).decode()})
    db_conn.commit()


def claim_job():
    """Commit the claim before processing; crashed workers' claims expire after six hours."""
    result = db_conn.execute(text(f"""
        WITH claimable AS (
            SELECT id FROM clickhouse_query_jobs
             WHERE failed_at IS NULL
               AND (claimed_at IS NULL
                    OR claimed_at < now() - interval '{CLAIM_TIMEOUT_HOURS} hours')
             ORDER BY created, id
             LIMIT 1
             FOR UPDATE SKIP LOCKED
        )
        UPDATE clickhouse_query_jobs SET claimed_at = now()
         WHERE id = (SELECT id FROM claimable)
         RETURNING *
    """))
    job = result.first()
    db_conn.commit()
    return job


def release_job(job):
    db_conn.execute(text("""
        UPDATE clickhouse_query_jobs SET claimed_at = NULL
         WHERE id = :id AND claimed_at = :claimed_at
    """), {"id": job.id, "claimed_at": job.claimed_at})
    db_conn.commit()


def fail_job(job):
    """Retain a failed job for inspection, without making it eligible for retry."""
    db_conn.execute(text("""
        UPDATE clickhouse_query_jobs SET failed_at = now()
         WHERE id = :id AND claimed_at = :claimed_at
    """), {"id": job.id, "claimed_at": job.claimed_at})
    db_conn.commit()


def remove_job(job):
    db_conn.execute(text("""
        DELETE FROM clickhouse_query_jobs WHERE id = :id AND claimed_at = :claimed_at
    """), {"id": job.id, "claimed_at": job.claimed_at})
    db_conn.commit()
