import { existsSync } from "node:fs";
import { resolve } from "node:path";

import dotenv from "dotenv";

const dotenvCandidates = [
  process.env.DOTENV_CONFIG_PATH,
  resolve(process.cwd(), ".env"),
  resolve(process.cwd(), "../../.env"),
].filter((value): value is string => Boolean(value));

for (const candidate of dotenvCandidates) {
  if (existsSync(candidate)) {
    dotenv.config({ path: candidate });
    break;
  }
}

const read = (name: string, fallback?: string): string => {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
};

export const config = {
  port: Number(process.env.ORCHESTRATOR_PORT ?? 3000),
  databaseUrl: read("DATABASE_URL"),
  rabbitmqUrl: read("RABBITMQ_URL"),
  rabbitmqExchange: read("RABBITMQ_EXCHANGE", "lce.events"),
  auditQueue: read("RABBITMQ_AUDIT_QUEUE", "audit.integration-events"),
  outboxPollIntervalMs: Number(process.env.OUTBOX_POLL_INTERVAL_MS ?? 2000),
};
