import type { PrismaClient } from "@prisma/client";
import amqp, { type Channel, type ChannelModel } from "amqplib";

import {
  BLUEPRINT_VALIDATED_EVENT_TYPE,
  GENERATION_REQUESTED_EVENT_TYPE,
  SITEMAP_UPDATED_EVENT_TYPE,
  TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
  TOPIC_QUALIFIED_EVENT_TYPE,
} from "@lce/shared-types";

import { config } from "./config";

export class OutboxRelay {
  private channel: Channel | null = null;
  private connection: ChannelModel | null = null;
  private intervalId: NodeJS.Timeout | null = null;
  private isPolling = false;
  private brokerRetryDelayMs = 1_000;
  private brokerRetryAt = 0;

  constructor(private readonly prisma: PrismaClient) {}

  start(): void {
    if (this.intervalId) {
      return;
    }

    this.intervalId = setInterval(() => {
      void this.flush();
    }, config.outboxPollIntervalMs);

    void this.flush();
  }

  async stop(): Promise<void> {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    await this.channel?.close().catch(() => undefined);
    await this.connection?.close().catch(() => undefined);
    this.channel = null;
    this.connection = null;
  }

  async flush(): Promise<void> {
    if (this.isPolling) {
      return;
    }

    if (Date.now() < this.brokerRetryAt) {
      return;
    }

    this.isPolling = true;

    try {
      await this.ensureBroker();

      const events = await this.prisma.outboxEvent.findMany({
        where: { processed: false },
        orderBy: { createdAt: "asc" },
        take: 20,
      });

      for (const event of events) {
        const published = this.channel?.publish(
          config.rabbitmqExchange,
          event.eventType,
          Buffer.from(JSON.stringify(event.payload)),
          {
            contentType: "application/json",
            deliveryMode: 2,
            messageId: event.id,
            timestamp: Date.now(),
            type: event.eventType,
          },
        );

        if (!published) {
          throw new Error(`Failed to publish outbox event ${event.id}`);
        }

        await this.prisma.outboxEvent.update({
          where: { id: event.id },
          data: {
            processed: true,
            processedAt: new Date(),
          },
        });
      }
    } catch (error) {
      if (isRetryableBrokerError(error)) {
        console.warn(
          `Outbox relay broker not ready; retrying in ${this.brokerRetryDelayMs}ms (${formatBrokerError(error)})`,
        );
        this.brokerRetryAt = Date.now() + this.brokerRetryDelayMs;
        this.brokerRetryDelayMs = Math.min(this.brokerRetryDelayMs * 2, 10_000);
      } else {
        console.error("Outbox relay flush failed", error);
      }
      await this.resetBroker();
    } finally {
      this.isPolling = false;
    }
  }

  getStatus(): {
    state: "ready" | "retrying" | "disconnected";
    retryDelayMs: number;
    retryAt: number | null;
    connected: boolean;
  } {
    const connected = Boolean(this.channel && this.connection);
    const retrying = Date.now() < this.brokerRetryAt;
    return {
      state: connected ? "ready" : retrying ? "retrying" : "disconnected",
      retryDelayMs: this.brokerRetryDelayMs,
      retryAt: this.brokerRetryAt > 0 ? this.brokerRetryAt : null,
      connected,
    };
  }

  private async ensureBroker(): Promise<void> {
    if (this.channel) {
      return;
    }

    const connection = await amqp.connect(config.rabbitmqUrl);
    connection.on("error", () => {
      void this.resetBroker();
    });
    connection.on("close", () => {
      void this.resetBroker();
    });
    this.connection = connection;

    const channel = await connection.createChannel();
    await channel.assertExchange(config.rabbitmqExchange, "direct", {
      durable: true,
    });
    await channel.assertQueue(config.generationQueue, {
      durable: true,
    });
    for (const eventType of [
      GENERATION_REQUESTED_EVENT_TYPE,
      TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
      TOPIC_QUALIFIED_EVENT_TYPE,
      SITEMAP_UPDATED_EVENT_TYPE,
      BLUEPRINT_VALIDATED_EVENT_TYPE,
    ]) {
      await channel.bindQueue(
        config.generationQueue,
        config.rabbitmqExchange,
        eventType,
      );
    }
    this.channel = channel;
    this.brokerRetryDelayMs = 1_000;
    this.brokerRetryAt = 0;
  }

  private async resetBroker(): Promise<void> {
    await this.channel?.close().catch(() => undefined);
    await this.connection?.close().catch(() => undefined);
    this.channel = null;
    this.connection = null;
  }
}

function isRetryableBrokerError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }

  return (
    "code" in error
    || /ECONNRESET|ECONNREFUSED|Socket closed abruptly|Channel ended|Connection closing/i.test(
      error.message,
    )
  );
}

function formatBrokerError(error: unknown): string {
  if (error instanceof Error) {
    const code =
      typeof (error as Error & { code?: unknown }).code === "string"
        ? (error as Error & { code?: string }).code
        : undefined;
    return code ? `${code}: ${error.message}` : error.message;
  }

  return String(error);
}
