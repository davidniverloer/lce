import type { PrismaClient } from "@prisma/client";
import amqp, { type Channel, type ChannelModel } from "amqplib";

import {
  GENERATION_REQUESTED_EVENT_TYPE,
} from "@lce/shared-types";

import { config } from "./config";

export class OutboxRelay {
  private channel: Channel | null = null;
  private connection: ChannelModel | null = null;
  private intervalId: NodeJS.Timeout | null = null;
  private isPolling = false;

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
      console.error("Outbox relay flush failed", error);
      await this.resetBroker();
    } finally {
      this.isPolling = false;
    }
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
    await channel.bindQueue(
      config.generationQueue,
      config.rabbitmqExchange,
      GENERATION_REQUESTED_EVENT_TYPE,
    );
    this.channel = channel;
  }

  private async resetBroker(): Promise<void> {
    await this.channel?.close().catch(() => undefined);
    await this.connection?.close().catch(() => undefined);
    this.channel = null;
    this.connection = null;
  }
}
