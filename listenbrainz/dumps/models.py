import logging
import os
from enum import StrEnum
from typing import Iterable, IO

from brainzutils import musicbrainz_db
from psycopg2.sql import Identifier, Composable, SQL
from pydantic import BaseModel, validator, root_validator
from sqlalchemy import Engine

from listenbrainz import db
from listenbrainz.db import timescale

logger = logging.getLogger(__name__)


class DumpEngineName(StrEnum):
    """ An enumeration representing different dump engines. """
    lb = "lb"
    ts = "ts"
    mb = "mb"


class DumpFormat(StrEnum):
    """ Enumeration for different postgres table dump formats. """
    text = "text"
    csv = "csv"


class DumpTable(BaseModel):
    """
    Represents a data model for managing PostgreSQL table dump operations.

    This class provides mechanisms to define table and column information, handle
    file-based export and import of table data, and supports operations related to
    PostgreSQL table dumps.
    """
    # todo: fix table_name and columns types after migration to pydantic v2 using Annotated + BeforeValidator
    table_name: str | Identifier
    columns: tuple[str | Composable, ...]
    filename: str | None = None
    file_format: str | None = None

    class Config:
        arbitrary_types_allowed = True

    @validator("table_name", pre=True, allow_reuse=True)
    def parse_table_name_field(cls, _table_name: str | Identifier) -> Identifier:
        """
        Parse and validate the `table_name` field.

        This function is a Pydantic validator for the `table_name` field. It checks
        the type of the input and ensures it is of type `str` or `Identifier`. If the
        input is a `str`, it is converted into an `Identifier` instance by splitting
        the string by the '.' delimiter. If the input is already an `Identifier`, it
        is returned as is. Any other type will raise a `TypeError`.

        Args:
            _table_name: The input field value to be validated.

        Returns:
            Identifier instance corresponding to the provided input.

        Raises:
            TypeError: If the input is neither a string nor an `Identifier`.
        """
        if isinstance(_table_name, Identifier):
            return _table_name
        elif isinstance(_table_name, str):
            return Identifier(*_table_name.split("."))
        else:
            raise TypeError("table_name must be a str or Identifier")

    @validator("columns", pre=True, allow_reuse=True)
    def parse_columns_fields(cls, _columns: Iterable[str | Composable]) -> Iterable[Composable]:
        """
        Validator function to parse and validate `columns` field input, transforming it into an
        iterable of `Composable` objects. Processes each input element to ensure it matches the
        required type, converting where necessary. If no input is provided, it returns an empty
        tuple.

        Parameters:
            cls: This refers to the class object to which the validation belongs. Typically passed
                 implicitly when used as a class method.
            _columns: Iterable of str or Composable
                The input field representing columns. Each element is expected to be either a
                `str` or a `Composable` object. If a string is encountered, it is converted to an
                `Identifier` object.

        Returns:
            Iterable[Composable]: Returns a tuple containing validated `Composable` objects.
        """
        if not _columns:
            return []

        fields = []
        for column in _columns:
            if isinstance(column, Composable):
                fields.append(column)
            else:
                fields.append(Identifier(column))

        return tuple(fields)

    @root_validator(pre=False)
    def set_filename_if_missing(cls, values):
        """
        This method is intended to validate the data provided for the object. It checks if the
        filename attribute is not provided (None) and assigns it a value based on the table_name
        attribute. This ensures that every instance has an appropriate filename even if it is not
        explicitly supplied.

        Parameters
        ----------
        values : dict
            A dictionary of attribute names and their current values for an instance being validated.

        Returns
        -------
        dict
            The updated values dictionary after potentially setting the filename.
        """
        table_name = values.get("table_name")
        filename = values.get("filename")

        if filename is None:
            values["filename"] = ".".join(table_name.strings)

        return values

    def get_fields(self):
        """ Joins the columns into a string separated by commas for SQL interpolation. """
        return SQL(",").join(self.columns)

    def export(self, cursor, location: str):
        """ Copies a PostgreSQL table to a file

            Arguments:
                cursor: a psycopg cursor
                location: the directory where the table should be copied
        """
        with open(os.path.join(location, self.filename), "w") as f:
            query = "COPY (SELECT {fields} FROM {table}) TO STDOUT"
            if self.file_format == DumpFormat.csv:
                query += " WITH CSV HEADER"
            query = SQL(query).format(
                fields=self.get_fields(),
                table=self.table_name
            )
            cursor.copy_expert(query, f)

    def _import(self, cursor, fp: IO[bytes]):
        """ Copies a file to a PostgreSQL table

            Arguments:
                cursor: a psycopg cursor
                fp: a file-like object containing the data to be imported
        """
        query = SQL("COPY {table}({fields}) FROM STDIN").format(
            fields=self.get_fields(),
            table=self.table_name
        )
        cursor.copy_expert(query, fp)


class DumpTablesCollection(BaseModel):
    """
    Represents a collection of tables to be dumped from a specific database engine.

    This class manages the association of a database engine with its respective
    tables to be exported.

    Attributes:
        engine_name: An enum indicating the name of the database engine used for
                     dumping the tables.
        tables: A list of DumpTable objects representing the tables to be exported.
    """
    engine_name: DumpEngineName
    tables: list[DumpTable]

    def get_engine(self) -> Engine:
        if self.engine_name == DumpEngineName.ts:
            return timescale.engine
        elif self.engine_name == DumpEngineName.lb:
            return db.engine
        else:
            return musicbrainz_db.engine

    def dump_tables(self, archive_tables_dir: str):
        """
        Dump tables to the specified directory in their individual files.

        Args:
            archive_tables_dir (str): Directory path where the tables should be exported.
        """
        engine = self.get_engine()
        with engine.connect() as connection, connection.begin() as transaction:
            cursor = connection.connection.cursor()
            for table in self.tables:
                try:
                    table.export(cursor=cursor, location=archive_tables_dir)
                except Exception:
                    logger.error("Error while copying table %s: ", table, exc_info=True)
                    raise
            transaction.rollback()
