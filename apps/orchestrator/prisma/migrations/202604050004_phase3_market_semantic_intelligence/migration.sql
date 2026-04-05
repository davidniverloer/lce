CREATE TABLE "market"."market_analysis_requests" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "seed_topic" TEXT NOT NULL,
    "target_audience" TEXT,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "market_analysis_requests_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "market"."qualified_topics" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "analysis_request_id" UUID NOT NULL,
    "topic" TEXT NOT NULL,
    "score" DOUBLE PRECISION NOT NULL,
    "trend_score" DOUBLE PRECISION NOT NULL,
    "social_score" DOUBLE PRECISION NOT NULL,
    "seo_score" DOUBLE PRECISION NOT NULL,
    "qualification_note" TEXT NOT NULL,
    "source_metadata" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "qualified_topics_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."sitemap_ingestions" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "sitemap_url" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sitemap_ingestions_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."indexed_pages" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "sitemap_ingestion_id" UUID NOT NULL,
    "url" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "indexed_pages_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."article_blueprints" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "qualified_topic_id" UUID NOT NULL,
    "sitemap_ingestion_id" UUID NOT NULL,
    "topic" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "blueprint_json" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "article_blueprints_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."internal_links" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "blueprint_id" UUID NOT NULL,
    "url" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "anchor_text" TEXT NOT NULL,
    "rationale" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "internal_links_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "content"."generation_tasks"
ADD COLUMN "qualified_topic_id" UUID,
ADD COLUMN "blueprint_id" UUID,
ADD COLUMN "blueprint_json" JSONB;

CREATE INDEX "market_analysis_requests_organization_id_id_idx" ON "market"."market_analysis_requests"("organization_id", "id");
CREATE INDEX "market_analysis_requests_campaign_id_id_idx" ON "market"."market_analysis_requests"("campaign_id", "id");
CREATE INDEX "qualified_topics_organization_id_id_idx" ON "market"."qualified_topics"("organization_id", "id");
CREATE INDEX "qualified_topics_campaign_id_score_idx" ON "market"."qualified_topics"("campaign_id", "score");
CREATE INDEX "qualified_topics_analysis_request_id_idx" ON "market"."qualified_topics"("analysis_request_id");
CREATE INDEX "sitemap_ingestions_organization_id_id_idx" ON "content"."sitemap_ingestions"("organization_id", "id");
CREATE INDEX "sitemap_ingestions_campaign_id_id_idx" ON "content"."sitemap_ingestions"("campaign_id", "id");
CREATE INDEX "indexed_pages_organization_id_sitemap_ingestion_id_idx" ON "content"."indexed_pages"("organization_id", "sitemap_ingestion_id");
CREATE INDEX "indexed_pages_campaign_id_id_idx" ON "content"."indexed_pages"("campaign_id", "id");
CREATE UNIQUE INDEX "article_blueprints_qualified_topic_id_key" ON "content"."article_blueprints"("qualified_topic_id");
CREATE INDEX "article_blueprints_organization_id_id_idx" ON "content"."article_blueprints"("organization_id", "id");
CREATE INDEX "article_blueprints_campaign_id_id_idx" ON "content"."article_blueprints"("campaign_id", "id");
CREATE INDEX "internal_links_organization_id_blueprint_id_idx" ON "content"."internal_links"("organization_id", "blueprint_id");
CREATE INDEX "internal_links_campaign_id_id_idx" ON "content"."internal_links"("campaign_id", "id");

ALTER TABLE "market"."market_analysis_requests"
ADD CONSTRAINT "market_analysis_requests_campaign_id_fkey"
FOREIGN KEY ("campaign_id") REFERENCES "campaign"."campaigns"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "market"."qualified_topics"
ADD CONSTRAINT "qualified_topics_campaign_id_fkey"
FOREIGN KEY ("campaign_id") REFERENCES "campaign"."campaigns"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "content"."sitemap_ingestions"
ADD CONSTRAINT "sitemap_ingestions_campaign_id_fkey"
FOREIGN KEY ("campaign_id") REFERENCES "campaign"."campaigns"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE "content"."article_blueprints"
ADD CONSTRAINT "article_blueprints_campaign_id_fkey"
FOREIGN KEY ("campaign_id") REFERENCES "campaign"."campaigns"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
