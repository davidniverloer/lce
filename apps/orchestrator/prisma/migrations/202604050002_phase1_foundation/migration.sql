CREATE SCHEMA IF NOT EXISTS "iam";
CREATE SCHEMA IF NOT EXISTS "campaign";
CREATE SCHEMA IF NOT EXISTS "market";
CREATE SCHEMA IF NOT EXISTS "content";
CREATE SCHEMA IF NOT EXISTS "repository";
CREATE SCHEMA IF NOT EXISTS "audit";

CREATE TABLE "iam"."organizations" (
    "id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "organizations_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "campaign"."campaigns" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "campaigns_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "audit"."outbox_events" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "event_type" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "processed" BOOLEAN NOT NULL DEFAULT false,
    "processed_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "outbox_events_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "audit"."processed_event_log" (
    "organization_id" UUID NOT NULL,
    "event_id" UUID NOT NULL,
    "consumer_name" TEXT NOT NULL,
    "processed_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "processed_event_log_pkey" PRIMARY KEY ("organization_id", "event_id", "consumer_name")
);

CREATE TABLE "audit"."event_receipts" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "event_id" UUID NOT NULL,
    "event_type" TEXT NOT NULL,
    "consumer_name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "event_receipts_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "organizations_id_idx" ON "iam"."organizations"("id");
CREATE INDEX "campaigns_organization_id_id_idx" ON "campaign"."campaigns"("organization_id", "id");
CREATE INDEX "outbox_events_organization_id_id_idx" ON "audit"."outbox_events"("organization_id", "id");
CREATE INDEX "outbox_events_processed_created_at_idx" ON "audit"."outbox_events"("processed", "created_at");
CREATE INDEX "event_receipts_organization_id_event_id_idx" ON "audit"."event_receipts"("organization_id", "event_id");

ALTER TABLE "campaign"."campaigns"
ADD CONSTRAINT "campaigns_organization_id_fkey"
FOREIGN KEY ("organization_id") REFERENCES "iam"."organizations"("id")
ON DELETE RESTRICT ON UPDATE CASCADE;
