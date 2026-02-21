"""Abstract base class for state managers."""

from abc import ABC, abstractmethod
from typing import Optional, Any


class BaseStateManager(ABC):
    @abstractmethod
    def save(self, job_id: str, state: dict) -> None: ...

    @abstractmethod
    def load(self, job_id: str) -> Optional[dict]: ...

    @abstractmethod
    def update(self, job_id: str, delta: dict) -> None: ...

    @abstractmethod
    def delete(self, job_id: str) -> None: ...
