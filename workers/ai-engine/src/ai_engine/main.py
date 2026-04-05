from __future__ import annotations

import logging

from .config import get_settings
from .db import create_session_factory
from .llm import create_llm_provider
from .runtime import prepare_crewai_runtime

prepare_crewai_runtime()

from .consumer import IntegrationEventConsumer


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    settings = get_settings()
    logging.getLogger(__name__).info(
        "Starting ai-engine worker llm_mode=%s market_signal_mode=%s llm_model=%s",
        settings.llm_mode,
        settings.market_signal_mode,
        settings.llm_model,
    )
    session_factory = create_session_factory(settings.database_url)
    llm_provider = create_llm_provider(settings)
    consumer = IntegrationEventConsumer(settings, session_factory, llm_provider)
    consumer.run_forever()


if __name__ == "__main__":
    main()
