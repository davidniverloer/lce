CREATE TABLE "content"."generation_tasks" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "topic" TEXT NOT NULL,
    "target_audience" TEXT,
    "output_formats" JSONB NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "completed_at" TIMESTAMP(3),
    CONSTRAINT "generation_tasks_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."generation_runs" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "task_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "status" TEXT NOT NULL,
    "state_json" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "generation_runs_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."draft_revisions" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "task_id" UUID NOT NULL,
    "run_id" UUID NOT NULL,
    "revision_number" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "draft_revisions_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "content"."qa_feedback" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "task_id" UUID NOT NULL,
    "run_id" UUID NOT NULL,
    "revision_number" INTEGER NOT NULL,
    "passed" BOOLEAN NOT NULL,
    "feedback" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "qa_feedback_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "repository"."articles" (
    "id" UUID NOT NULL,
    "organization_id" UUID NOT NULL,
    "campaign_id" UUID NOT NULL,
    "task_id" UUID NOT NULL,
    "title" TEXT NOT NULL,
    "body" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "articles_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "generation_tasks_organization_id_id_idx" ON "content"."generation_tasks"("organization_id", "id");
CREATE INDEX "generation_tasks_campaign_id_id_idx" ON "content"."generation_tasks"("campaign_id", "id");
CREATE UNIQUE INDEX "generation_runs_task_id_key" ON "content"."generation_runs"("task_id");
CREATE INDEX "generation_runs_organization_id_id_idx" ON "content"."generation_runs"("organization_id", "id");
CREATE UNIQUE INDEX "draft_revisions_task_id_revision_number_key" ON "content"."draft_revisions"("task_id", "revision_number");
CREATE INDEX "draft_revisions_organization_id_task_id_idx" ON "content"."draft_revisions"("organization_id", "task_id");
CREATE UNIQUE INDEX "qa_feedback_task_id_revision_number_key" ON "content"."qa_feedback"("task_id", "revision_number");
CREATE INDEX "qa_feedback_organization_id_task_id_idx" ON "content"."qa_feedback"("organization_id", "task_id");
CREATE UNIQUE INDEX "articles_task_id_key" ON "repository"."articles"("task_id");
CREATE INDEX "articles_organization_id_id_idx" ON "repository"."articles"("organization_id", "id");

ALTER TABLE "content"."generation_tasks"
ADD CONSTRAINT "generation_tasks_campaign_id_fkey"
FOREIGN KEY ("campaign_id") REFERENCES "campaign"."campaigns"("id")
ON DELETE RESTRICT ON UPDATE CASCADE;
