import asyncio
import threading
from threading import Lock
from typing import Type, TypeVar

T = TypeVar("T")


def singleton_with_lock(cls: Type[T]):
    instances = {}
    lock = Lock()

    def get_instance(*args, **kwargs) -> T:
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
            return instances[cls]

    return get_instance
