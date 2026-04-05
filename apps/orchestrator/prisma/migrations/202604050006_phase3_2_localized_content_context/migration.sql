ALTER TABLE "market"."market_analysis_requests"
ADD COLUMN "content_language" TEXT,
ADD COLUMN "geo_context" TEXT;

ALTER TABLE "content"."generation_tasks"
ADD COLUMN "content_language" TEXT,
ADD COLUMN "geo_context" TEXT;
