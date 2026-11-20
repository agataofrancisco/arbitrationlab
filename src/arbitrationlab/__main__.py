"""Ponto de entrada: `python -m arbitrationlab` arranca a API com uvicorn."""

from __future__ import annotations

import uvicorn

from arbitrationlab.api.app import create_app


def main() -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
