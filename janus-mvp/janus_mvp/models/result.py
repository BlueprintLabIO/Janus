from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar


T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Result(Generic[T, E]):
    value: Optional[T] = None
    error: Optional[E] = None

    @property
    def is_success(self) -> bool:
        return self.error is None

    @staticmethod
    def ok(value: T) -> "Result[T, E]":
        return Result(value=value, error=None)

    @staticmethod
    def fail(error: E) -> "Result[T, E]":
        return Result(value=None, error=error)

