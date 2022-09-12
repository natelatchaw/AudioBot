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


class Demerit(Storable[int]):

    __slots__ = [
        'user_id',
        'author_id',
        'timestamp',
        'reason',
        'details'
    ]

    user_id: int

    author_id: int

    timestamp: datetime

    reason: str

    details: str

    def __init__(self, snowflake: int, user_id: int, author_id: int, timestamp: datetime, reason: str, details: str):
        self.id: int = snowflake
        self.user_id: int = user_id
        self.author_id: int = author_id
        self.timestamp: datetime = timestamp
        self.reason: str = reason
        self.details: str = details
        

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
