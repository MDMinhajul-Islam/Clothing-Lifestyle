"""Request-scoped Retell latency diagnostics with no payload or secret logging."""

import hashlib
import logging
import time
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("retell.timing")


@dataclass
class TimingTrace:
    request_id: str
    started: float
    last_stage: float


_trace: ContextVar[TimingTrace | None] = ContextVar("retell_timing_trace", default=None)


def begin() -> Token:
    now = time.perf_counter()
    token = _trace.set(TimingTrace(f"rtf-{uuid.uuid4().hex[:12]}", now, now))
    mark("request_received")
    return token


def finish(token: Token) -> None:
    mark("request_complete")
    _trace.reset(token)


def mark(stage: str, *, duration_ms: float | None = None, **fields: Any) -> None:
    trace = _trace.get()
    if trace is None:
        return
    now = time.perf_counter()
    stage_ms = duration_ms if duration_ms is not None else (now - trace.last_stage) * 1000
    total_ms = (now - trace.started) * 1000
    trace.last_stage = now
    suffix = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    logger.info("request_id=%s stage=%s stage_ms=%.2f total_ms=%.2f%s",
                trace.request_id, stage, stage_ms, total_ms, f" {suffix}" if suffix else "")


def timed(stage: str, started: float, **fields: Any) -> None:
    mark(stage, duration_ms=(time.perf_counter() - started) * 1000, **fields)


class TimedCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, variables=None):
        started = time.perf_counter()
        try:
            return self._cursor.execute(query, variables)
        finally:
            text = str(query)
            timed("database_query", started, operation=text.lstrip().split(None, 1)[0].upper() if text.strip() else "UNKNOWN",
                  query_id=hashlib.sha256(text.encode("utf-8")).hexdigest()[:10])

    def executemany(self, query, variables):
        started = time.perf_counter()
        try:
            return self._cursor.executemany(query, variables)
        finally:
            text = str(query)
            timed("database_query_many", started,
                  operation=text.lstrip().split(None, 1)[0].upper() if text.strip() else "UNKNOWN",
                  query_id=hashlib.sha256(text.encode("utf-8")).hexdigest()[:10])

    def callproc(self, procname, parameters=None):
        started = time.perf_counter()
        try:
            return self._cursor.callproc(procname, parameters)
        finally:
            timed("database_procedure", started,
                  query_id=hashlib.sha256(str(procname).encode("utf-8")).hexdigest()[:10])

    def __enter__(self):
        self._cursor.__enter__()
        return self

    def __exit__(self, *args):
        return self._cursor.__exit__(*args)

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class TimedConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self, *args, **kwargs):
        return TimedCursor(self._connection.cursor(*args, **kwargs))

    def commit(self):
        started = time.perf_counter()
        try:
            return self._connection.commit()
        finally:
            timed("database_commit", started)

    def rollback(self):
        started = time.perf_counter()
        try:
            return self._connection.rollback()
        finally:
            timed("database_rollback", started)

    def __getattr__(self, name):
        return getattr(self._connection, name)
