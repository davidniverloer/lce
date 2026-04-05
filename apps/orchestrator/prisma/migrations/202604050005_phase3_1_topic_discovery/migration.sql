ALTER TABLE "market"."market_analysis_requests"
ALTER COLUMN "seed_topic" DROP NOT NULL;

ALTER TABLE "market"."market_analysis_requests"
ADD COLUMN "industry" TEXT,
ADD COLUMN "auto_discover" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN "discovered_topics" JSONB;
