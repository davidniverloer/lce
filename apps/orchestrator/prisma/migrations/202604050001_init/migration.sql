CREATE TABLE "campaigns" (
    "id" UUID NOT NULL,
    "organization_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "niche" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "campaigns_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "topics" (
    "id" UUID NOT NULL,
    "organization_id" TEXT NOT NULL,
    "campaign_id" UUID NOT NULL,
    "title" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "topics_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "outbox_events" (
    "id" UUID NOT NULL,
    "organization_id" TEXT NOT NULL,
    "event_type" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "processed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "outbox_events_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "processed_event_log" (
    "organization_id" TEXT NOT NULL,
    "event_id" TEXT NOT NULL,
    "consumer_name" TEXT NOT NULL,
    "processed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "processed_event_log_pkey" PRIMARY KEY ("organization_id", "event_id", "consumer_name")
);

CREATE INDEX "campaigns_organization_id_id_idx" ON "campaigns"("organization_id", "id");
CREATE INDEX "topics_organization_id_id_idx" ON "topics"("organization_id", "id");
CREATE INDEX "topics_organization_id_campaign_id_idx" ON "topics"("organization_id", "campaign_id");
CREATE INDEX "outbox_events_organization_id_id_idx" ON "outbox_events"("organization_id", "id");
CREATE INDEX "outbox_events_processed_created_at_idx" ON "outbox_events"("processed", "created_at");
