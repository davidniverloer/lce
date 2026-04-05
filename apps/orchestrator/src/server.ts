import { createServer } from "node:http";

import { createApp } from "./app";
import { config } from "./config";
import { prisma } from "./db";
import { OutboxRelay } from "./outboxRelay";

const relay = new OutboxRelay(prisma);
const app = createApp({ relay });
const server = createServer(app);

server.listen(config.port, () => {
  console.log(`Orchestrator listening on http://localhost:${config.port}`);
  relay.start();
});

const shutdown = async () => {
  await relay.stop();
  await prisma.$disconnect();

  server.close(() => {
    process.exit(0);
  });
};

process.on("SIGINT", () => {
  void shutdown();
});

process.on("SIGTERM", () => {
  void shutdown();
});
