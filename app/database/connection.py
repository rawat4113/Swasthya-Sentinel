"""Small JSON-backed persistence layer used by the Swasthya Sentinel MVP.

The app previously used SQLAlchemy's Session API with SQLite. This module
retains the small subset of that API used by the app, while persisting records
as readable JSON in a single file. It is intended for a single-process local
or demo deployment, not concurrent multi-worker production use.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import BinaryExpression, UnaryExpression
from sqlalchemy.sql import operators

from app.core.config import settings


class Base(DeclarativeBase):
    """Model metadata base retained for the existing model declarations."""


_store_lock = threading.RLock()


def _default_path() -> Path:
    return Path(settings.database_file).expanduser().resolve()


def _empty_document() -> dict[str, Any]:
    return {"format_version": 1, "tables": {}, "sequences": {}}


def _read_document(path: Path | None = None) -> dict[str, Any]:
    target = path or _default_path()
    if not target.exists():
        return _empty_document()
    with target.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("tables"), dict):
        raise ValueError(f"JSON database has an invalid format: {target}")
    document.setdefault("format_version", 1)
    document.setdefault("sequences", {})
    return document


def _write_document(document: dict[str, Any], path: Path | None = None) -> None:
    target = path or _default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2, default=_json_default)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot encode {type(value).__name__} in JSON database")


def initialize_store() -> None:
    """Create the JSON file if it does not yet exist."""
    with _store_lock:
        path = _default_path()
        if not path.exists():
            _write_document(_empty_document(), path)


def _model_columns(model):
    return list(model.__table__.columns)


def _primary_key_name(model) -> str:
    return model.__mapper__.primary_key[0].key


def _column_defaults(model) -> dict[str, Any]:
    defaults = {}
    for column in _model_columns(model):
        if column.default is not None:
            value = column.default.arg
            if callable(value):
                try:
                    value = value()
                except TypeError:
                    try:
                        value = value(None)
                    except TypeError:
                        continue
            defaults[column.key] = value
    return defaults


def _decode_row(model, raw: dict[str, Any]):
    values = dict(raw)
    for column in _model_columns(model):
        value = values.get(column.key)
        if value is not None:
            try:
                if column.type.python_type is datetime and isinstance(value, str):
                    values[column.key] = datetime.fromisoformat(value)
            except (AttributeError, NotImplementedError):
                pass
    return model(**values)


def _encode_row(obj) -> dict[str, Any]:
    return {column.key: getattr(obj, column.key, None) for column in _model_columns(type(obj))}


def _expression_matches(expression, obj) -> bool:
    if isinstance(expression, BinaryExpression):
        key = getattr(expression.left, "key", None)
        if not key:
            return False
        lhs = getattr(obj, key, None)
        rhs = getattr(expression.right, "value", expression.right)
        operation = expression.operator
        if operation is operators.eq:
            return lhs == rhs
        if operation is operators.ne:
            return lhs != rhs
        if operation is operators.lt:
            return lhs is not None and rhs is not None and lhs < rhs
        if operation is operators.le:
            return lhs is not None and rhs is not None and lhs <= rhs
        if operation is operators.gt:
            return lhs is not None and rhs is not None and lhs > rhs
        if operation is operators.ge:
            return lhs is not None and rhs is not None and lhs >= rhs
        if operation is operators.is_:
            return lhs is rhs
        if operation is operators.is_not:
            return lhs is not rhs
        return False
    clauses = getattr(expression, "clauses", None)
    if clauses is not None:
        results = [_expression_matches(item, obj) for item in clauses]
        if getattr(expression, "operator", None) is operators.and_:
            return all(results)
        if getattr(expression, "operator", None) is operators.or_:
            return any(results)
    return False


def _sort_key(value):
    return (value is None, value)


class JSONQuery:
    def __init__(self, session: "JSONSession", model):
        self.session = session
        self.model = model
        self.predicates = []
        self.sorts = []
        self.row_limit = None

    def filter_by(self, **values):
        for key, value in values.items():
            self.predicates.append(lambda obj, k=key, v=value: getattr(obj, k, None) == v)
        return self

    def filter(self, *expressions):
        self.predicates.extend(expressions)
        return self

    def order_by(self, *expressions):
        self.sorts.extend(expressions)
        return self

    def limit(self, count: int):
        self.row_limit = max(0, int(count))
        return self

    def _all_unlimited(self):
        table = self.model.__tablename__
        rows = self.session.document["tables"].get(table, [])
        objects = []
        pk_name = _primary_key_name(self.model)
        for raw in rows:
            key = raw.get(pk_name)
            identity = (self.model, key)
            if identity in self.session.deleted:
                continue
            obj = self.session.identity.get(identity)
            if obj is None:
                obj = _decode_row(self.model, raw)
                self.session.identity[identity] = obj
            objects.append(obj)
        for obj in self.session.pending:
            if isinstance(obj, self.model) and obj not in objects:
                objects.append(obj)
        for predicate in self.predicates:
            if callable(predicate) and not isinstance(predicate, (BinaryExpression, UnaryExpression)):
                objects = [obj for obj in objects if predicate(obj)]
            else:
                objects = [obj for obj in objects if _expression_matches(predicate, obj)]
        for expression in reversed(self.sorts):
            descending = isinstance(expression, UnaryExpression) and expression.modifier is operators.desc_op
            column = expression.element if isinstance(expression, UnaryExpression) else expression
            key = getattr(column, "key", None)
            if key:
                objects.sort(key=lambda obj, k=key: _sort_key(getattr(obj, k, None)), reverse=descending)
        return objects

    def all(self):
        objects = self._all_unlimited()
        return objects if self.row_limit is None else objects[:self.row_limit]

    def first(self):
        objects = self._all_unlimited()
        return objects[0] if objects else None

    def count(self):
        return len(self.all())

    def delete(self, synchronize_session=False):
        objects = self.all()
        pk_name = _primary_key_name(self.model)
        for obj in objects:
            identity = (self.model, getattr(obj, pk_name, None))
            self.session.deleted.add(identity)
            if obj in self.session.pending:
                self.session.pending.remove(obj)
        return len(objects)


class JSONSession:
    """Session-like unit of work writing model rows into a JSON document."""
    def __init__(self):
        self.path = _default_path()
        with _store_lock:
            self.document = _read_document(self.path)
        self.identity = {}
        self.pending = []
        self.deleted = set()

    def query(self, model):
        return JSONQuery(self, model)

    def _assign_defaults(self, obj):
        for name, value in _column_defaults(type(obj)).items():
            if getattr(obj, name, None) is None:
                setattr(obj, name, value)

    def _assign_pk(self, obj):
        model = type(obj)
        pk_name = _primary_key_name(model)
        if getattr(obj, pk_name, None) is not None:
            return
        column = model.__table__.columns[pk_name]
        if not getattr(column, "autoincrement", False):
            return
        rows = self.document["tables"].get(model.__tablename__, [])
        current = max((int(row.get(pk_name) or 0) for row in rows), default=0)
        current = max(current, int(self.document.get("sequences", {}).get(model.__tablename__, 0)))
        for candidate in self.pending:
            if isinstance(candidate, model):
                current = max(current, int(getattr(candidate, pk_name, 0) or 0))
        setattr(obj, pk_name, current + 1)
        self.document.setdefault("sequences", {})[model.__tablename__] = current + 1

    def add(self, obj):
        self._assign_defaults(obj)
        self._assign_pk(obj)
        if obj not in self.pending and obj not in self.identity.values():
            self.pending.append(obj)
        return obj

    def add_all(self, objects):
        for obj in objects:
            self.add(obj)

    def get(self, model, primary_key):
        identity = (model, primary_key)
        if identity in self.deleted:
            return None
        if identity in self.identity:
            return self.identity[identity]
        for obj in self.pending:
            if isinstance(obj, model) and getattr(obj, _primary_key_name(model), None) == primary_key:
                return obj
        for raw in self.document["tables"].get(model.__tablename__, []):
            if raw.get(_primary_key_name(model)) == primary_key:
                obj = _decode_row(model, raw)
                self.identity[identity] = obj
                return obj
        return None

    def flush(self):
        for obj in self.pending:
            self._assign_defaults(obj)
            self._assign_pk(obj)
            self.identity[(type(obj), getattr(obj, _primary_key_name(type(obj))))] = obj

    def refresh(self, obj):
        self.flush()
        key_name = _primary_key_name(type(obj))
        key = getattr(obj, key_name)
        for raw in self.document["tables"].get(type(obj).__tablename__, []):
            if raw.get(key_name) == key:
                fresh = _decode_row(type(obj), raw)
                for column in _model_columns(type(obj)):
                    setattr(obj, column.key, getattr(fresh, column.key, None))
                break
        return obj

    def commit(self):
        self.flush()
        with _store_lock:
            latest = _read_document(self.path)
            for model, key in self.deleted:
                rows = latest["tables"].get(model.__tablename__, [])
                latest["tables"][model.__tablename__] = [
                    row for row in rows if row.get(_primary_key_name(model)) != key
                ]
            for obj in list(self.identity.values()) + list(self.pending):
                model = type(obj)
                table = model.__tablename__
                pk_name = _primary_key_name(model)
                key = getattr(obj, pk_name, None)
                if (model, key) in self.deleted:
                    continue
                row = _encode_row(obj)
                rows = latest["tables"].setdefault(table, [])
                for index, existing in enumerate(rows):
                    if existing.get(pk_name) == key:
                        rows[index] = row
                        break
                else:
                    rows.append(row)
                if isinstance(key, int):
                    latest.setdefault("sequences", {})[table] = max(
                        int(latest.get("sequences", {}).get(table, 0)), key
                    )
            _write_document(latest, self.path)
            self.document = latest
        self.pending.clear()
        self.deleted.clear()

    def rollback(self):
        with _store_lock:
            self.document = _read_document(self.path)
        self.identity.clear()
        self.pending.clear()
        self.deleted.clear()

    def close(self):
        self.identity.clear()
        self.pending.clear()
        self.deleted.clear()


SessionLocal = JSONSession


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
