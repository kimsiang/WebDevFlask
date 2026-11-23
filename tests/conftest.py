"""Isolated DB-API doubles: tests never contact a laboratory database."""

from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest
from flask import template_rendered


@dataclass
class Result:
    rows: tuple = ()
    columns: tuple = ()
    error: Exception | None = None


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = ()
        self.rows = ()
        self.closed = False

    def execute(self, sql, parameters=None):
        self.connection.queries.append((sql, parameters))
        result = self.connection.results.popleft() if self.connection.results else Result()
        if result.error:
            raise result.error
        self.rows = tuple(result.rows)
        self.description = tuple((column, None, None, None, None, None, None) for column in result.columns)
        return len(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class FakeConnection:
    def __init__(self, results=()):
        self.results = deque(results)
        self.queries = []
        self.cursors = []
        self.closed = False
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        cursor = FakeCursor(self)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        self.closed = True

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@dataclass
class DatabaseStub:
    connections: list = field(default_factory=list)
    planned_results: deque = field(default_factory=deque)
    connect_calls: list = field(default_factory=list)
    connect_error: Exception | None = None

    def queue(self, *results):
        self.planned_results.append(results)

    def connect(self, **kwargs):
        self.connect_calls.append(kwargs)
        if self.connect_error:
            raise self.connect_error
        connection = FakeConnection(self.planned_results.popleft() if self.planned_results else ())
        self.connections.append(connection)
        return connection


@pytest.fixture
def database_stub(monkeypatch):
    import pymysql

    stub = DatabaseStub()
    monkeypatch.setattr(pymysql, "connect", stub.connect)
    return stub


@contextmanager
def captured_templates(app):
    """Observe the real render, rather than replace it with a test-only stub."""
    templates = []

    def record(sender, template, context, **extra):
        templates.append((template.name, context))

    template_rendered.connect(record, app)
    try:
        yield templates
    finally:
        template_rendered.disconnect(record, app)


@pytest.fixture
def capture_templates():
    return captured_templates


@pytest.fixture
def app(database_stub):
    from app import create_app

    return create_app({"TESTING": True, "DB_USER": "test_reader", "DB_NAME": "test_db"})
