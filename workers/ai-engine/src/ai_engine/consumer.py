from __future__ import annotations

import json
import logging
import time

import pika
from pika import exceptions as pika_exceptions
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from sqlalchemy.orm import sessionmaker

from .config import Settings
from .handler import (
    parse_event,
    process_event,
)
from .llm import LLMProvider

LOGGER = logging.getLogger(__name__)
INITIAL_BROKER_RETRY_SECONDS = 1.0
MAX_BROKER_RETRY_SECONDS = 10.0


class IntegrationEventConsumer:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker,
        llm_provider: LLMProvider,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._llm_provider = llm_provider

    def run_forever(self) -> None:
        retry_delay = INITIAL_BROKER_RETRY_SECONDS
        while True:
            try:
                self._consume()
                retry_delay = INITIAL_BROKER_RETRY_SECONDS
            except KeyboardInterrupt:
                raise
            except pika_exceptions.AMQPConnectionError as exc:
                LOGGER.warning(
                    "RabbitMQ not ready for ai-engine worker; retrying in %.1f seconds (%s)",
                    retry_delay,
                    exc,
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, MAX_BROKER_RETRY_SECONDS)
            except Exception:
                LOGGER.exception(
                    "Worker loop failed unexpectedly; retrying in %.1f seconds",
                    retry_delay,
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, MAX_BROKER_RETRY_SECONDS)

    def _consume(self) -> None:
        parameters = pika.URLParameters(self._settings.rabbitmq_url)
        parameters.connection_attempts = 3
        parameters.retry_delay = 2
        parameters.socket_timeout = 5
        parameters.blocked_connection_timeout = 15
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(
            exchange=self._settings.rabbitmq_exchange,
            exchange_type="direct",
            durable=True,
        )
        channel.queue_declare(queue=self._settings.generation_queue, durable=True)
        channel.queue_bind(
            queue=self._settings.generation_queue,
            exchange=self._settings.rabbitmq_exchange,
            routing_key="GenerationRequested",
        )
        for routing_key in (
            "TopicGenerationRequested",
            "TopicQualified",
            "SitemapUpdated",
            "BlueprintValidated",
        ):
            channel.queue_bind(
                queue=self._settings.generation_queue,
                exchange=self._settings.rabbitmq_exchange,
                routing_key=routing_key,
            )
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self._settings.generation_queue,
            on_message_callback=self._on_message,
        )

        LOGGER.info("Consuming queue %s", self._settings.generation_queue)

        try:
            channel.start_consuming()
        finally:
            if channel.is_open:
                channel.close()
            if connection.is_open:
                connection.close()

    def _on_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        del properties

        try:
            raw_event = json.loads(body.decode("utf-8"))
            event = parse_event(raw_event)
            inserted = process_event(
                session_factory=self._session_factory,
                consumer_name=self._settings.consumer_name,
                settings=self._settings,
                event=event,
                llm_provider=self._llm_provider,
            )

            if inserted:
                LOGGER.info("Processed integration event %s", event.event_type)
            else:
                LOGGER.info("Skipped duplicate event %s", event.event_id)

            channel.basic_ack(delivery_tag=method.delivery_tag)
        except ValueError:
            LOGGER.exception("Discarding invalid integration event")
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            LOGGER.exception("Failed to process integration event; requeueing")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
