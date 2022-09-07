from datetime import datetime
from pathlib import Path
from sqlite3 import Row
from typing import Any, List, Tuple, Type

import discord

from database.column import ColumnBuilder
from database.database import Database
from database.storable import Storable, TStorable
from database.table import Table, TableBuilder
from settings import Settings


class Demerit(Storable):
    def __init__(self, snowflake: int, user_id: int, author_id: int, timestamp: datetime, reason: str, details: str):
        self._snowflake: int = snowflake
        self._user_id: int = user_id
        self._author_id: int = author_id
        self._timestamp: datetime = timestamp
        self._reason: str = reason
        self._details: str = details

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def author_id(self) -> int:
        return self._author_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def details(self) -> str:
        return self._details

    
    @classmethod
    def __table__(self) -> Table:
        # create a table builder
        t_builder: TableBuilder = TableBuilder()
        # set the table's name
        t_builder.setName('Demerits')

        # create a column builder
        c_builder: ColumnBuilder = ColumnBuilder()
        # create Snowflake column
        t_builder.addColumn(c_builder.setName('Snowflake').setType('INTEGER').isPrimary().isUnique().column())
        # create user ID column
        t_builder.addColumn(c_builder.setName('UserID').setType('INTEGER').column())
        # create author ID column
        t_builder.addColumn(c_builder.setName('AuthorID').setType('INTEGER').column())
        # create timestamp column
        t_builder.addColumn(c_builder.setName('Timestamp').setType('TIMESTAMP').column())
        # create title column
        t_builder.addColumn(c_builder.setName('Reason').setType('TEXT').column())
        # create description column
        t_builder.addColumn(c_builder.setName('Details').setType('TEXT').column())
        
        # build the table
        table: Table = t_builder.table()
        # return the table
        return table


    def __values__(self) -> Tuple[Any, ...]:
        # create a tuple with the corresponding values
        value: Tuple[Any, ...] = (self._snowflake, self._user_id, self._author_id, self._timestamp, self._reason, self._details)
        # return the tuple
        return value
        

    @classmethod
    def __from_row__(cls: Type[TStorable], row: Row) -> TStorable:
        # Get snowflake value from the row
        snowflake: int = row['Snowflake']
        # Get user_id value from the row
        user_id: int = row['UserID']
        # Get author_id value from the row
        author_id: int = row['AuthorID']
        # Get timestamp value from the row
        timestamp: datetime = row['Timestamp']
        # Get title value from the row
        title: str = row['Reason']
        # Get description value from the row
        description: str = row['Details']
        # return the Demerit
        return Demerit(snowflake, user_id, author_id, timestamp, title, description)
    

class DemeritManager():
    
    def __init__(self, settings: Settings):
        # create database instance
        self._database: Database = Database(Path('./archive/demerit.db'))
        # create the database
        self._database.create(Demerit)

    async def post(self, demerit: Demerit) -> None:
        # insert the demerit
        self._database.insert(demerit)

    async def get(self, user_id: int) -> List[Demerit]:
        # select all demerit rows
        demerits: List[Demerit] = [Demerit.__from_row__(row) for row in self._database.select(Demerit)]
        # filter demerits by the provided user id
        return [demerit for demerit in demerits if demerit.user_id == user_id]
