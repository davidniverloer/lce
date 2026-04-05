from __future__ import annotations

import logging

from .config import get_settings
from .db import create_session_factory
from .llm import create_llm_provider
from .runtime import prepare_crewai_runtime

prepare_crewai_runtime()

from .consumer import GenerationRequestedConsumer


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()
    session_factory = create_session_factory(settings.database_url)
    llm_provider = create_llm_provider(settings)
    consumer = GenerationRequestedConsumer(settings, session_factory, llm_provider)
    consumer.run_forever()


if __name__ == "__main__":
    main()
