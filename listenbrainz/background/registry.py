from dataclasses import dataclass
from datetime import timedelta
from typing import Callable


@dataclass(frozen=True)
class TaskType:
    """ A type of background task and how the worker runs it.

    Each task type has its own worker threads, which claim only tasks of this type, so a slow
    type can't take every thread.
    """
    name: str
    handler: Callable
    threads: int
    max_attempts: int
    timeout: timedelta


TASKS: dict[str, TaskType] = {}


def task(name: str, *, threads: int, max_attempts: int, timeout: timedelta):
    """ Register the decorated function as the handler of a background task type.

    Args:
        name: the value stored in background_tasks.task for this type
        threads: the number of worker threads that run tasks of this type
        max_attempts: after this many failed attempts the task is marked failed
        timeout: a claim older than this is treated as a crashed worker and released

    The handler is called as handler(db_conn, listens_conn, task_row).
    """
    def decorator(handler):
        if name in TASKS:
            raise ValueError(f"Background task {name} is already registered")
        TASKS[name] = TaskType(name, handler, threads, max_attempts, timeout)
        return handler
    return decorator
