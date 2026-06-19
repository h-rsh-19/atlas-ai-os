from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class TinyTableSchema:
    name: str
    columns: tuple[str, ...]
    primary_key: str = "id"


@dataclass
class TinyOperation:
    op: str
    table: str
    key: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class TinyAtlasDatabase:
    """A tiny in-memory database kernel used as an Atlas systems-learning lab.

    This is not intended to replace SQLite/PostgreSQL. It is a transparent
    implementation of core database ideas: schema checks, primary-key indexing,
    append-only operation logging, point reads, scans, updates, and deletes.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, TinyTableSchema] = {}
        self._tables: dict[str, dict[str, dict[str, Any]]] = {}
        self._wal: list[TinyOperation] = []

    def create_table(
        self,
        name: str,
        columns: list[str] | tuple[str, ...],
        *,
        primary_key: str = "id",
    ) -> TinyTableSchema:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Table name must be alphanumeric or underscore.")
        column_tuple = tuple(dict.fromkeys(columns))
        if primary_key not in column_tuple:
            raise ValueError("Primary key must be one of the table columns.")
        if name in self._schemas:
            raise ValueError(f"Table already exists: {name}")

        schema = TinyTableSchema(name=name, columns=column_tuple, primary_key=primary_key)
        self._schemas[name] = schema
        self._tables[name] = {}
        self._wal.append(TinyOperation("create_table", name, name, {"columns": list(column_tuple)}))
        return schema

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        schema = self._schema(table)
        self._validate_row(schema, row, partial=False)
        key = str(row[schema.primary_key])
        if key in self._tables[table]:
            raise ValueError(f"Duplicate primary key: {key}")
        stored = {column: row.get(column) for column in schema.columns}
        self._tables[table][key] = stored
        self._wal.append(TinyOperation("insert", table, key, stored.copy()))
        return stored.copy()

    def get(self, table: str, key: str) -> dict[str, Any] | None:
        row = self._tables_for(table).get(str(key))
        return row.copy() if row else None

    def update(self, table: str, key: str, patch: dict[str, Any]) -> dict[str, Any]:
        schema = self._schema(table)
        if str(key) not in self._tables[table]:
            raise KeyError(f"Missing row: {key}")
        self._validate_row(schema, patch, partial=True)
        if schema.primary_key in patch and str(patch[schema.primary_key]) != str(key):
            raise ValueError("Primary key updates are not supported.")
        self._tables[table][str(key)].update(patch)
        updated = self._tables[table][str(key)].copy()
        self._wal.append(TinyOperation("update", table, str(key), patch.copy()))
        return updated

    def delete(self, table: str, key: str) -> bool:
        rows = self._tables_for(table)
        existed = str(key) in rows
        if existed:
            deleted = rows.pop(str(key))
            self._wal.append(TinyOperation("delete", table, str(key), deleted.copy()))
        return existed

    def scan(self, table: str) -> list[dict[str, Any]]:
        return [row.copy() for row in self._tables_for(table).values()]

    def where(self, table: str, **conditions: Any) -> list[dict[str, Any]]:
        rows = self._tables_for(table).values()
        return [
            row.copy()
            for row in rows
            if all(row.get(column) == value for column, value in conditions.items())
        ]

    def explain(self) -> dict[str, Any]:
        return {
            "tables": {
                name: {
                    "columns": list(schema.columns),
                    "primary_key": schema.primary_key,
                    "rows": len(self._tables[name]),
                }
                for name, schema in self._schemas.items()
            },
            "wal_entries": len(self._wal),
            "last_operation": self._wal[-1].op if self._wal else None,
            "index_type": "hash map primary-key index",
        }

    def _schema(self, table: str) -> TinyTableSchema:
        try:
            return self._schemas[table]
        except KeyError as exc:
            raise KeyError(f"Unknown table: {table}") from exc

    def _tables_for(self, table: str) -> dict[str, dict[str, Any]]:
        self._schema(table)
        return self._tables[table]

    @staticmethod
    def _validate_row(schema: TinyTableSchema, row: dict[str, Any], *, partial: bool) -> None:
        unknown = set(row) - set(schema.columns)
        if unknown:
            raise ValueError(f"Unknown columns for {schema.name}: {sorted(unknown)}")
        if partial:
            return
        missing = [column for column in schema.columns if column not in row]
        if missing:
            raise ValueError(f"Missing columns for {schema.name}: {missing}")
