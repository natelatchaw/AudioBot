
from abc import abstractmethod
from datetime import datetime
import functools
from itertools import chain
from sqlite3 import Row
from typing import Any, Callable, Dict, Generic, List, Tuple, Type, TypeVar, get_type_hints
from database.column import ColumnBuilder

from database.table import Table, TableBuilder


TStorable = TypeVar('TStorable', bound='Storable')
"""
A type variable representing an object conforming to the
Storable protocol.
"""

TIdentifier = TypeVar('TIdentifier')
"""
"""


MAPPINGS: Dict[type, str] = {
    str:        'TEXT',
    int:        'INTEGER',
    datetime:   'TIMESTAMP',
    TIdentifier:'INTEGER'
}



class Storable(Generic[TIdentifier]):
    """
    A protocol defining methods to create and manipulate SQL tables
    based off of an object.
    """

    __slots__ = ['id']

    __types__: Dict[str, str] = {}

    
    id: TIdentifier
    """
    The identifier to use as the unique primary key.
    """

    def __init__(self, id: TIdentifier) -> None:
        self.id = id

    
    @classmethod
    def __table__(cls: Type[TStorable]) -> Table:
        """
        This method is responsible for returning a Table instance.
        This is used by the Database class to create a table.
        """
        
        slots: List[str] = chain.from_iterable(getattr(type, '__slots__', []) for type in cls.__mro__)
        
        # create a table builder
        t_builder: TableBuilder = TableBuilder()
        # set the table's name to the class name
        t_builder.setName(cls.__name__)

        # for each slot property
        for slot in slots:            
            # get the property's name
            property_name: str = getattr(cls, slot).__name__
            # get the property's type
            property_type: type = get_type_hints(cls)[slot]
            # get whether the property name is 'id'
            is_identifier: bool = property_name == 'id'

            # create a column builder
            c_builder: ColumnBuilder = ColumnBuilder()
            # set the column's name to the property name
            c_builder = c_builder.setName(property_name).setType(MAPPINGS[property_type])
            # determine whether to set the column as primary
            c_builder = c_builder.isPrimary(is_identifier).isUnique(is_identifier)
            # add the column to the table
            t_builder.addColumn(c_builder.column())

        return t_builder.table()


    def __values__(self) -> Tuple[Any, ...]:
        """
        This method is responsible for returning an n-tuple
        containing all storable instance properties.
        
        Properties should be in the same order as defined by
        the Table column definitions returned by __table__().
        """
        
        cls: Type[TStorable] = self.__class__
        slots: List[str] = chain.from_iterable(getattr(type, '__slots__', []) for type in cls.__mro__)
        
        return tuple(getattr(self, slot) for slot in slots)


    @classmethod
    @abstractmethod
    def __from_row__(cls: Type[TStorable], row: Row) -> TStorable:
        """
        This method is responsible for initializing an instance of
        TStorable from the provided Row object.
        """
        ...