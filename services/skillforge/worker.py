
import asyncio

from .config import PRODUCTION
from .migrate import migrate, require_current_schema
from .scanning import run_scans


def main():
    if PRODUCTION:
        require_current_schema()
    else:
        migrate()
    asyncio.run(run_scans())


if __name__ == "__main__":
    main()
