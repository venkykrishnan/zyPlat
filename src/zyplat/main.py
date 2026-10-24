"""Uvicorn entrypoint. The database URL comes from ``ZYPLAT_DATABASE_URL``."""

import uvicorn

from zyplat.app import create_app

app = create_app()


def main() -> None:
    uvicorn.run("zyplat.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
