from __future__ import annotations

import logging

from .config import get_settings
from .consumer import IntegrationEventConsumer
from .db import create_session_factory


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    consumer = IntegrationEventConsumer(settings, session_factory)
    consumer.run_forever()


if __name__ == "__main__":
    main()
