
import asyncio

from .config import PRODUCTION
from .db import close
from .migrate import migrate, require_current_schema
from .scanning import run_scans


def main():
    try:
        (require_current_schema if PRODUCTION else migrate)()
        asyncio.run(run_scans())
    finally:
        close()


if __name__ == "__main__":
    main()
