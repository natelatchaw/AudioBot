import asyncio
from collections import deque
from typing import Generic, Iterable, Iterator, Optional, TypeVar

RequestType = TypeVar('RequestType')

class Queue(Generic[RequestType], Iterable[RequestType]):

    @property
    def current(self) -> Optional[RequestType]:
        """
        The current request, if any.
        """
        return self._current

    def __init__(self) -> None:
        """
        Initialize the queue.
        """

        self._queue: asyncio.Queue[RequestType] = asyncio.Queue()
        self._deque: deque[RequestType] = deque()
        self._current: Optional[RequestType] = None
        super().__init__()

    async def put(self, item: RequestType) -> None:
        """
        Put a request into the queue.
        """
        await self._queue.put(item)
        self._deque.append(item)

    async def get(self) -> RequestType:
        """
        Get the next request in the queue.
        """
        self._current = None
        item: RequestType = await self._queue.get()
        self._current = self._deque.popleft()
        return item
    
    async def clear(self) -> None:
        """
        Clear the queue of all requests.
        """
        self._current = None
        self._deque.clear()

    def __iter__(self) -> Iterator[RequestType]:
        return self._deque.__iter__()