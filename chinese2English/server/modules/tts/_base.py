import abc
from collections.abc import AsyncIterator


class TTSBackend(abc.ABC):
    @abc.abstractmethod
    async def load(self) -> None: ...

    @abc.abstractmethod
    async def synthesize(self, text: str) -> AsyncIterator[bytes]: ...

    @abc.abstractmethod
    async def synthesize_full(self, text: str) -> bytes: ...
