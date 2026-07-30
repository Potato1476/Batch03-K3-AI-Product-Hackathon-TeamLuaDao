"""CHẮN public /v1 API."""

__all__ = ["create_app"]


def __getattr__(name: str):
    if name == "create_app":
        from .main import create_app

        return create_app
    raise AttributeError(name)
