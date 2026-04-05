import { randomUUID } from "node:crypto";

import { Prisma } from "@prisma/client";
import express, { type NextFunction, type Request, type Response } from "express";

import {
  CAMPAIGN_CREATED_EVENT_TYPE,
  GENERATION_REQUESTED_EVENT_TYPE,
  INTEGRATION_EVENT_VERSION,
  ORGANIZATION_CREATED_EVENT_TYPE,
  SITEMAP_UPDATED_EVENT_TYPE,
  TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
  type ArticleBlueprintSnapshot,
  type CampaignCreatedEvent,
  type GenerationRequestedEvent,
  type OrganizationCreatedEvent,
  type SitemapUpdatedEvent,
  type TopicGenerationRequestedEvent,
} from "@lce/shared-types";

import { prisma } from "./db";
import type { OutboxRelay } from "./outboxRelay";

const getString = (value: unknown): string | null =>
  typeof value === "string" && value.trim().length > 0 ? value.trim() : null;

const getStringArray = (value: unknown): string[] | null => {
  if (!Array.isArray(value)) {
    return null;
  }

  const items = value.filter((item): item is string => typeof item === "string");
  return items.length === value.length ? items : null;
};

const createOrganizationCreatedEvent = (
  organizationId: string,
  name: string,
): OrganizationCreatedEvent => ({
  eventId: randomUUID(),
  eventType: ORGANIZATION_CREATED_EVENT_TYPE,
  version: INTEGRATION_EVENT_VERSION,
  timestamp: new Date().toISOString(),
  payload: {
    organizationId,
    name,
  },
});

const createCampaignCreatedEvent = (
  organizationId: string,
  campaignId: string,
  name: string,
): CampaignCreatedEvent => ({
  eventId: randomUUID(),
  eventType: CAMPAIGN_CREATED_EVENT_TYPE,
  version: INTEGRATION_EVENT_VERSION,
  timestamp: new Date().toISOString(),
  payload: {
    organizationId,
    campaignId,
    name,
  },
});

const createGenerationRequestedEvent = (
  organizationId: string,
  campaignId: string,
  taskId: string,
  topic: string,
  targetAudience: string | null,
  contentLanguage: string | null,
  geoContext: string | null,
  outputFormats: string[],
  blueprintId?: string | null,
  blueprint?: ArticleBlueprintSnapshot | null,
): GenerationRequestedEvent => ({
  eventId: randomUUID(),
  eventType: GENERATION_REQUESTED_EVENT_TYPE,
  version: INTEGRATION_EVENT_VERSION,
  timestamp: new Date().toISOString(),
  payload: {
    organizationId,
    campaignId,
    taskId,
    topic,
    targetAudience,
    contentLanguage,
    geoContext,
    outputFormats,
    blueprintId: blueprintId ?? null,
    blueprint: blueprint ?? null,
  },
});

const createTopicGenerationRequestedEvent = (
  organizationId: string,
  campaignId: string,
  analysisRequestId: string,
  seedTopic: string | null,
  industry: string | null,
  autoDiscover: boolean,
  targetAudience: string | null,
  contentLanguage: string | null,
  geoContext: string | null,
): TopicGenerationRequestedEvent => ({
  eventId: randomUUID(),
  eventType: TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
  version: INTEGRATION_EVENT_VERSION,
  timestamp: new Date().toISOString(),
  payload: {
    organizationId,
    campaignId,
    analysisRequestId,
    seedTopic,
    industry,
    autoDiscover,
    targetAudience,
    contentLanguage,
    geoContext,
  },
});

const createSitemapUpdatedEvent = (
  organizationId: string,
  campaignId: string,
  sitemapIngestionId: string,
  sitemapUrl: string,
  indexedPageCount: number,
): SitemapUpdatedEvent => ({
  eventId: randomUUID(),
  eventType: SITEMAP_UPDATED_EVENT_TYPE,
  version: INTEGRATION_EVENT_VERSION,
  timestamp: new Date().toISOString(),
  payload: {
    organizationId,
    campaignId,
    sitemapIngestionId,
    sitemapUrl,
    indexedPageCount,
  },
});

const defaultSitemapXml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/library/content-operations</loc></url>
  <url><loc>https://example.com/library/revision-checklist</loc></url>
  <url><loc>https://example.com/library/internal-linking-playbook</loc></url>
</urlset>`;

const extractTagValues = (xml: string, tagName: string): string[] => {
  const pattern = new RegExp(`<${tagName}>(.*?)</${tagName}>`, "gims");
  return Array.from(xml.matchAll(pattern), (match) => match[1]?.trim() ?? "")
    .filter((value) => value.length > 0);
};

const titleFromUrl = (input: string): string => {
  try {
    const url = new URL(input);
    const slug = url.pathname.split("/").filter(Boolean).pop() ?? "page";

    return slug
      .split(/[-_]/g)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  } catch {
    return "Indexed Page";
  }
};

const parseSitemapXml = (xml: string) =>
  extractTagValues(xml, "loc").map((url) => ({
    url,
    title: titleFromUrl(url),
  }));

const loadSitemap = async (sitemapUrl: string) => {
  if (sitemapUrl === "fixture://default-sitemap") {
    return parseSitemapXml(defaultSitemapXml);
  }

  const response = await fetch(sitemapUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch sitemap: ${response.status} ${response.statusText}`);
  }

  const xml = await response.text();
  return parseSitemapXml(xml);
};

type CreateAppOptions = {
  relay?: OutboxRelay;
};

export const createApp = (options: CreateAppOptions = {}) => {
  const app = express();
  const prismaExtended = prisma as typeof prisma & {
    marketAnalysisRequest: any;
    qualifiedTopic: any;
    generationRun: any;
    generationTask: any;
    repositoryArticle: any;
    sitemapIngestion: any;
    indexedPage: any;
    articleBlueprint: any;
    internalLink: any;
  };

  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({
      status: "ok",
      infra: {
        relay: options.relay?.getStatus() ?? {
          state: "disconnected",
          retryDelayMs: 0,
          retryAt: null,
          connected: false,
        },
      },
    });
  });

  app.get("/fixtures/sitemap.xml", (_req, res) => {
    res.type("application/xml").send(defaultSitemapXml);
  });

  app.post("/organizations", async (req, res, next) => {
    const name = getString(req.body?.name);

    if (!name) {
      res.status(400).json({ error: "name is required" });
      return;
    }

    try {
      const organization = await prisma.$transaction(async (tx) => {
        const createdOrganization = await tx.organization.create({
          data: { name },
        });

        const event = createOrganizationCreatedEvent(
          createdOrganization.id,
          createdOrganization.name,
        );

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId: createdOrganization.id,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return createdOrganization;
      });

      res.status(201).json({
        id: organization.id,
        name: organization.name,
        createdAt: organization.createdAt,
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/organizations/:organizationId", async (req, res, next) => {
    try {
      const organization = await prisma.organization.findUnique({
        where: { id: req.params.organizationId },
      });

      if (!organization) {
        res.status(404).json({ error: "organization not found" });
        return;
      }

      res.json({
        id: organization.id,
        name: organization.name,
        createdAt: organization.createdAt,
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/organizations/:organizationId/campaigns", async (req, res, next) => {
    const name = getString(req.body?.name);

    if (!name) {
      res.status(400).json({ error: "name is required" });
      return;
    }

    try {
      const campaign = await prisma.$transaction(async (tx) => {
        const organization = await tx.organization.findUnique({
          where: { id: req.params.organizationId },
        });

        if (!organization) {
          return null;
        }

        const createdCampaign = await tx.campaign.create({
          data: {
            organizationId: organization.id,
            name,
          },
        });

        const event = createCampaignCreatedEvent(
          organization.id,
          createdCampaign.id,
          createdCampaign.name,
        );

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId: organization.id,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return createdCampaign;
      });

      if (!campaign) {
        res.status(404).json({ error: "organization not found" });
        return;
      }

      res.status(201).json({
        id: campaign.id,
        organizationId: campaign.organizationId,
        name: campaign.name,
        createdAt: campaign.createdAt,
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/organizations/:organizationId/campaigns", async (req, res, next) => {
    try {
      const organization = await prisma.organization.findUnique({
        where: { id: req.params.organizationId },
      });

      if (!organization) {
        res.status(404).json({ error: "organization not found" });
        return;
      }

      const campaigns = await prisma.campaign.findMany({
        where: {
          organizationId: organization.id,
        },
        orderBy: {
          createdAt: "asc",
        },
      });

      res.json({
        organizationId: organization.id,
        campaigns: campaigns.map((campaign) => ({
          id: campaign.id,
          name: campaign.name,
          createdAt: campaign.createdAt,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/market/analyze", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);
    const campaignId = getString(req.query.campaignId);

    if (!organizationId || !campaignId) {
      res.status(400).json({ error: "organizationId and campaignId are required" });
      return;
    }

    try {
      const analysisRequest = await prismaExtended.marketAnalysisRequest.findFirst({
        where: {
          organizationId,
          campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      const topics = await prismaExtended.qualifiedTopic.findMany({
        where: {
          organizationId,
          campaignId,
        },
        orderBy: [{ score: "desc" }, { createdAt: "asc" }],
      });

      res.json({
        organizationId,
        campaignId,
        statusArtifact: analysisRequest
          ? {
              discovery: {
                mode:
                  analysisRequest.discoveredTopics?.[0]?.sourceMetadata?.mode ?? "seed_topic",
                sources:
                  analysisRequest.discoveredTopics?.flatMap(
                    (candidate: any) => candidate?.sourceMetadata?.discoverySources ?? [],
                  ) ?? [],
              },
              qualification: {
                topicCount: topics.length,
                fallbackCount: topics.reduce(
                  (count: number, topic: any) =>
                    count +
                    Number(
                      topic?.sourceMetadata?.status?.qualification?.fallbackCount ?? 0,
                    ),
                  0,
                ),
              },
            }
          : null,
        analysisRequest: analysisRequest
          ? {
              analysisRequestId: analysisRequest.id,
              seedTopic: analysisRequest.seedTopic,
              industry: analysisRequest.industry,
              autoDiscover: analysisRequest.autoDiscover,
              discoveredTopics: analysisRequest.discoveredTopics,
              targetAudience: analysisRequest.targetAudience,
              contentLanguage: analysisRequest.contentLanguage,
              geoContext: analysisRequest.geoContext,
              status: analysisRequest.status,
            }
          : null,
        qualifiedTopics: topics.map((topic: any) => ({
          id: topic.id,
          topic: topic.topic,
          score: topic.score,
          trendScore: topic.trendScore,
          socialScore: topic.socialScore,
          seoScore: topic.seoScore,
          qualificationNote: topic.qualificationNote,
          sourceMetadata: topic.sourceMetadata,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/market/analyze", async (req, res, next) => {
    const organizationId = getString(req.body?.organizationId);
    const campaignId = getString(req.body?.campaignId);
    const seedTopic = getString(req.body?.seedTopic);
    const industry = getString(req.body?.industry);
    const targetAudience = getString(req.body?.targetAudience);
    const contentLanguage = getString(req.body?.contentLanguage);
    const geoContext = getString(req.body?.geoContext);
    const autoDiscover = !seedTopic;

    if (!organizationId || !campaignId || (!seedTopic && !industry)) {
      res.status(400).json({
        error: "organizationId, campaignId, and either seedTopic or industry are required",
      });
      return;
    }

    try {
      const analysisRequest = await prisma.$transaction(async (tx) => {
        const campaign = await tx.campaign.findFirst({
          where: {
            id: campaignId,
            organizationId,
          },
        });

        if (!campaign) {
          return null;
        }

        const createdRequest = await (tx as typeof prismaExtended).marketAnalysisRequest.create({
          data: {
            organizationId,
            campaignId,
            seedTopic,
            industry,
            autoDiscover,
            targetAudience,
            contentLanguage,
            geoContext,
            status: "queued",
          },
        });

        const event = createTopicGenerationRequestedEvent(
          organizationId,
          campaignId,
          createdRequest.id,
          seedTopic,
          industry,
          autoDiscover,
          targetAudience,
          contentLanguage,
          geoContext,
        );

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return createdRequest;
      });

      if (!analysisRequest) {
        res.status(404).json({ error: "campaign not found" });
        return;
      }

      res.status(202).json({
        analysisRequestId: analysisRequest.id,
        organizationId: analysisRequest.organizationId,
        campaignId: analysisRequest.campaignId,
        seedTopic: analysisRequest.seedTopic,
        industry: analysisRequest.industry,
        autoDiscover: analysisRequest.autoDiscover,
        contentLanguage: analysisRequest.contentLanguage,
        geoContext: analysisRequest.geoContext,
        status: analysisRequest.status,
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/sitemap/ingest", async (req, res, next) => {
    const organizationId = getString(req.body?.organizationId);
    const campaignId = getString(req.body?.campaignId);
    const sitemapUrl = getString(req.body?.sitemapUrl);

    if (!organizationId || !campaignId || !sitemapUrl) {
      res.status(400).json({
        error: "organizationId, campaignId, and sitemapUrl are required",
      });
      return;
    }

    try {
      const campaign = await prisma.campaign.findFirst({
        where: {
          id: campaignId,
          organizationId,
        },
      });

      if (!campaign) {
        res.status(404).json({ error: "campaign not found" });
        return;
      }

      const indexedPages = await loadSitemap(sitemapUrl);
      if (indexedPages.length === 0) {
        res.status(400).json({ error: "sitemap did not contain any indexed pages" });
        return;
      }

      const ingestion = await prisma.$transaction(async (tx) => {
        const createdIngestion = await (tx as typeof prismaExtended).sitemapIngestion.create({
          data: {
            organizationId,
            campaignId,
            sitemapUrl,
            status: "ready",
          },
        });

        await (tx as typeof prismaExtended).indexedPage.createMany({
          data: indexedPages.map((page) => ({
            id: randomUUID(),
            organizationId,
            campaignId,
            sitemapIngestionId: createdIngestion.id,
            url: page.url,
            title: page.title,
          })),
        });

        const event = createSitemapUpdatedEvent(
          organizationId,
          campaignId,
          createdIngestion.id,
          sitemapUrl,
          indexedPages.length,
        );

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return createdIngestion;
      });

      res.status(201).json({
        sitemapIngestionId: ingestion.id,
        organizationId: ingestion.organizationId,
        campaignId: ingestion.campaignId,
        status: ingestion.status,
        indexedPageCount: indexedPages.length,
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/qualified-topics", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const topics = await prismaExtended.qualifiedTopic.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: [{ score: "desc" }, { createdAt: "asc" }],
      });

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        qualifiedTopics: topics.map((topic: any) => ({
          id: topic.id,
          topic: topic.topic,
          score: topic.score,
          trendScore: topic.trendScore,
          socialScore: topic.socialScore,
          seoScore: topic.seoScore,
          qualificationNote: topic.qualificationNote,
          sourceMetadata: topic.sourceMetadata,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/indexed-pages", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const pages = await prismaExtended.indexedPage.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "asc",
        },
      });

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        indexedPages: pages.map((page: any) => ({
          id: page.id,
          url: page.url,
          title: page.title,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/blueprints", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const blueprints = await prismaExtended.articleBlueprint.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        blueprints: blueprints.map((blueprint: any) => ({
          id: blueprint.id,
          qualifiedTopicId: blueprint.qualifiedTopicId,
          topic: blueprint.topic,
          status: blueprint.status,
          blueprint: blueprint.blueprintJson,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/tasks", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const tasks = await prismaExtended.generationTask.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        tasks: tasks.map((task: any) => ({
          id: task.id,
          topic: task.topic,
          status: task.status,
          blueprintId: task.blueprintId,
          completedAt: task.completedAt,
        })),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/status-summary", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const tasks = await prismaExtended.generationTask.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      const taskIds = tasks.map((task: any) => task.id);
      const qualifiedTopicIds = tasks
        .map((task: any) => task.qualifiedTopicId)
        .filter((value: string | null | undefined): value is string => Boolean(value));

      const [runs, qualifiedTopics, articles] = await Promise.all([
        prismaExtended.generationRun.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
        prismaExtended.qualifiedTopic.findMany({
          where: {
            id: { in: qualifiedTopicIds },
          },
        }),
        prismaExtended.repositoryArticle.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
      ]);

      const runsByTaskId = new Map<string, any>(
        runs.map((run: any) => [run.taskId, run]),
      );
      const qualifiedTopicsById = new Map<string, any>(
        qualifiedTopics.map((topic: any) => [topic.id, topic]),
      );
      const articlesByTaskId = new Map<string, any>(
        articles.map((article: any) => [article.taskId, article]),
      );

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        summaries: tasks.map((task: any) => {
          const run = runsByTaskId.get(task.id);
          const runState = run?.stateJson as Record<string, any> | undefined;
          const qualifiedTopic = task.qualifiedTopicId
            ? qualifiedTopicsById.get(task.qualifiedTopicId)
            : null;
          const qualificationStatus =
            (qualifiedTopic?.sourceMetadata as Record<string, any> | undefined)?.status ?? null;
          const blueprint = task.blueprintJson as Record<string, any> | null;
          const article = articlesByTaskId.get(task.id);
          const generationStatus =
            (runState?.statusArtifact as Record<string, any> | undefined) ?? null;
          const discovery = qualificationStatus?.discovery ?? null;
          const qualification = qualificationStatus?.qualification ?? null;

          return {
            taskId: task.id,
            topic: task.topic,
            taskStatus: task.status,
            articleStatus: article?.status ?? null,
            articleId: article?.id ?? null,
            confidenceScore: qualification?.confidenceScore ?? null,
            confidenceBand: qualification?.confidenceBand ?? null,
            fallbackWeightShare: qualification?.fallbackWeightShare ?? null,
            fallbackCount: qualification?.fallbackCount ?? null,
            discoveryMode: discovery?.mode ?? null,
            discoverySources: discovery?.sources ?? null,
            differentiationReady: blueprint?.status?.differentiationReady ?? null,
            sitemapUsed: blueprint?.status?.sitemapUsed ?? null,
            siteAware: blueprint?.status?.siteAware ?? null,
            qaStatus: generationStatus?.generation?.qaStatus ?? null,
            qaPassed: generationStatus?.generation?.qaPassed ?? null,
          };
        }),
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/status-trends", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const tasks = await prismaExtended.generationTask.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      const taskIds = tasks.map((task: any) => task.id);
      const qualifiedTopicIds = tasks
        .map((task: any) => task.qualifiedTopicId)
        .filter((value: string | null | undefined): value is string => Boolean(value));

      const [runs, qualifiedTopics, articles] = await Promise.all([
        prismaExtended.generationRun.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
        prismaExtended.qualifiedTopic.findMany({
          where: {
            id: { in: qualifiedTopicIds },
          },
        }),
        prismaExtended.repositoryArticle.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
      ]);

      const runsByTaskId = new Map<string, any>(
        runs.map((run: any) => [run.taskId, run]),
      );
      const qualifiedTopicsById = new Map<string, any>(
        qualifiedTopics.map((topic: any) => [topic.id, topic]),
      );
      const articlesByTaskId = new Map<string, any>(
        articles.map((article: any) => [article.taskId, article]),
      );

      const taskStatusCounts: Record<string, number> = {};
      const discoverySourceCounts = new Map<string, number>();
      let confidenceScoreTotal = 0;
      let confidenceScoreCount = 0;
      let fallbackWeightShareTotal = 0;
      let fallbackWeightShareCount = 0;
      let articleCompletedCount = 0;
      let differentiationReadyCount = 0;
      let siteAwareCount = 0;
      let qaPassCount = 0;

      for (const task of tasks) {
        taskStatusCounts[task.status] = (taskStatusCounts[task.status] ?? 0) + 1;

        const run = runsByTaskId.get(task.id);
        const runState = run?.stateJson as Record<string, any> | undefined;
        const generationStatus =
          (runState?.statusArtifact as Record<string, any> | undefined) ?? null;
        const article = articlesByTaskId.get(task.id);
        const blueprint = task.blueprintJson as Record<string, any> | null;
        const qualifiedTopic = task.qualifiedTopicId
          ? qualifiedTopicsById.get(task.qualifiedTopicId)
          : null;
        const qualificationStatus =
          (qualifiedTopic?.sourceMetadata as Record<string, any> | undefined)?.status ?? null;
        const discovery = qualificationStatus?.discovery ?? null;
        const qualification = qualificationStatus?.qualification ?? null;
        const discoverySources = Array.isArray(discovery?.sources) ? discovery.sources : [];

        for (const source of discoverySources) {
          if (typeof source !== "string" || source.length === 0) {
            continue;
          }

          discoverySourceCounts.set(
            source,
            (discoverySourceCounts.get(source) ?? 0) + 1,
          );
        }

        if (typeof qualification?.confidenceScore === "number") {
          confidenceScoreTotal += qualification.confidenceScore;
          confidenceScoreCount += 1;
        }

        if (typeof qualification?.fallbackWeightShare === "number") {
          fallbackWeightShareTotal += qualification.fallbackWeightShare;
          fallbackWeightShareCount += 1;
        }

        if (article?.status === "completed") {
          articleCompletedCount += 1;
        }

        if (blueprint?.status?.differentiationReady === true) {
          differentiationReadyCount += 1;
        }

        if (blueprint?.status?.siteAware === true) {
          siteAwareCount += 1;
        }

        if (generationStatus?.generation?.qaPassed === true) {
          qaPassCount += 1;
        }
      }

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        metrics: {
          totalTasks: tasks.length,
          taskStatusCounts,
          articleCompletedCount,
          averageConfidenceScore:
            confidenceScoreCount > 0 ? confidenceScoreTotal / confidenceScoreCount : null,
          averageFallbackWeightShare:
            fallbackWeightShareCount > 0
              ? fallbackWeightShareTotal / fallbackWeightShareCount
              : null,
          differentiationReadyCount,
          siteAwareCount,
          qaPassCount,
          qaPassRate: tasks.length > 0 ? qaPassCount / tasks.length : null,
          topDiscoverySources: Array.from(discoverySourceCounts.entries())
            .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
            .slice(0, 5)
            .map(([source, count]) => ({ source, count })),
        },
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:campaignId/status-compare", async (req, res, next) => {
    const organizationId = getString(req.query.organizationId);
    const requestedWindow = Number.parseInt(String(req.query.window ?? "3"), 10);
    const windowSize =
      Number.isFinite(requestedWindow) && requestedWindow > 0 ? requestedWindow : 3;

    if (!organizationId) {
      res.status(400).json({ error: "organizationId is required" });
      return;
    }

    try {
      const tasks = await prismaExtended.generationTask.findMany({
        where: {
          organizationId,
          campaignId: req.params.campaignId,
        },
        orderBy: {
          createdAt: "desc",
        },
      });

      const taskIds = tasks.map((task: any) => task.id);
      const qualifiedTopicIds = tasks
        .map((task: any) => task.qualifiedTopicId)
        .filter((value: string | null | undefined): value is string => Boolean(value));

      const [runs, qualifiedTopics, articles] = await Promise.all([
        prismaExtended.generationRun.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
        prismaExtended.qualifiedTopic.findMany({
          where: {
            id: { in: qualifiedTopicIds },
          },
        }),
        prismaExtended.repositoryArticle.findMany({
          where: {
            taskId: { in: taskIds },
          },
        }),
      ]);

      const runsByTaskId = new Map<string, any>(
        runs.map((run: any) => [run.taskId, run]),
      );
      const qualifiedTopicsById = new Map<string, any>(
        qualifiedTopics.map((topic: any) => [topic.id, topic]),
      );
      const articlesByTaskId = new Map<string, any>(
        articles.map((article: any) => [article.taskId, article]),
      );

      const summaries = tasks.map((task: any) => {
        const run = runsByTaskId.get(task.id);
        const runState = run?.stateJson as Record<string, any> | undefined;
        const qualifiedTopic = task.qualifiedTopicId
          ? qualifiedTopicsById.get(task.qualifiedTopicId)
          : null;
        const qualificationStatus =
          (qualifiedTopic?.sourceMetadata as Record<string, any> | undefined)?.status ?? null;
        const blueprint = task.blueprintJson as Record<string, any> | null;
        const article = articlesByTaskId.get(task.id);
        const generationStatus =
          (runState?.statusArtifact as Record<string, any> | undefined) ?? null;
        const discovery = qualificationStatus?.discovery ?? null;
        const qualification = qualificationStatus?.qualification ?? null;

        return {
          confidenceScore:
            typeof qualification?.confidenceScore === "number"
              ? qualification.confidenceScore
              : null,
          fallbackWeightShare:
            typeof qualification?.fallbackWeightShare === "number"
              ? qualification.fallbackWeightShare
              : null,
          differentiationReady: blueprint?.status?.differentiationReady === true,
          siteAware: blueprint?.status?.siteAware === true,
          qaPassed: generationStatus?.generation?.qaPassed === true,
          discoverySources: Array.isArray(discovery?.sources)
            ? discovery.sources.filter((source: unknown): source is string => typeof source === "string")
            : [],
          articleCompleted: article?.status === "completed",
        };
      });

      const latestWindow = summaries.slice(0, windowSize);
      const previousWindow = summaries.slice(windowSize, windowSize * 2);

      const aggregateWindow = (items: typeof summaries) => {
        const discoverySourceCounts = new Map<string, number>();
        let confidenceTotal = 0;
        let confidenceCount = 0;
        let fallbackTotal = 0;
        let fallbackCount = 0;
        let differentiationReadyCount = 0;
        let siteAwareCount = 0;
        let qaPassCount = 0;
        let articleCompletedCount = 0;

        for (const item of items) {
          if (typeof item.confidenceScore === "number") {
            confidenceTotal += item.confidenceScore;
            confidenceCount += 1;
          }

          if (typeof item.fallbackWeightShare === "number") {
            fallbackTotal += item.fallbackWeightShare;
            fallbackCount += 1;
          }

          if (item.differentiationReady) {
            differentiationReadyCount += 1;
          }

          if (item.siteAware) {
            siteAwareCount += 1;
          }

          if (item.qaPassed) {
            qaPassCount += 1;
          }

          if (item.articleCompleted) {
            articleCompletedCount += 1;
          }

          for (const source of item.discoverySources) {
            discoverySourceCounts.set(
              source,
              (discoverySourceCounts.get(source) ?? 0) + 1,
            );
          }
        }

        return {
          taskCount: items.length,
          articleCompletedCount,
          averageConfidenceScore:
            confidenceCount > 0 ? confidenceTotal / confidenceCount : null,
          averageFallbackWeightShare:
            fallbackCount > 0 ? fallbackTotal / fallbackCount : null,
          differentiationReadyRate:
            items.length > 0 ? differentiationReadyCount / items.length : null,
          siteAwareRate: items.length > 0 ? siteAwareCount / items.length : null,
          qaPassRate: items.length > 0 ? qaPassCount / items.length : null,
          topDiscoverySources: Array.from(discoverySourceCounts.entries())
            .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
            .slice(0, 5)
            .map(([source, count]) => ({ source, count })),
        };
      };

      const latest = aggregateWindow(latestWindow);
      const previous = aggregateWindow(previousWindow);

      res.json({
        organizationId,
        campaignId: req.params.campaignId,
        windowSize,
        latest,
        previous,
        delta: {
          averageConfidenceScoreChange:
            latest.averageConfidenceScore !== null && previous.averageConfidenceScore !== null
              ? latest.averageConfidenceScore - previous.averageConfidenceScore
              : null,
          averageFallbackWeightShareChange:
            latest.averageFallbackWeightShare !== null &&
            previous.averageFallbackWeightShare !== null
              ? latest.averageFallbackWeightShare - previous.averageFallbackWeightShare
              : null,
          qaPassRateChange:
            latest.qaPassRate !== null && previous.qaPassRate !== null
              ? latest.qaPassRate - previous.qaPassRate
              : null,
          differentiationReadyRateChange:
            latest.differentiationReadyRate !== null &&
            previous.differentiationReadyRate !== null
              ? latest.differentiationReadyRate - previous.differentiationReadyRate
              : null,
          siteAwareRateChange:
            latest.siteAwareRate !== null && previous.siteAwareRate !== null
              ? latest.siteAwareRate - previous.siteAwareRate
              : null,
          discoverySourceCountChange: latest.topDiscoverySources.map(({ source, count }) => {
            const previousCount =
              previous.topDiscoverySources.find((item) => item.source === source)?.count ?? 0;
            return {
              source,
              countChange: count - previousCount,
            };
          }),
        },
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/tasks/generate", async (req, res, next) => {
    const organizationId = getString(req.body?.organizationId);
    const campaignId = getString(req.body?.campaignId);
    const topic = getString(req.body?.topic);
    const targetAudience = getString(req.body?.targetAudience);
    const contentLanguage = getString(req.body?.contentLanguage);
    const geoContext = getString(req.body?.geoContext);
    const outputFormats =
      getStringArray(req.body?.outputFormats) ?? ["markdown_article"];

    if (!organizationId || !campaignId || !topic) {
      res
        .status(400)
        .json({ error: "organizationId, campaignId, and topic are required" });
      return;
    }

    try {
      const task = await prisma.$transaction(async (tx) => {
        const campaign = await tx.campaign.findFirst({
          where: {
            id: campaignId,
            organizationId,
          },
        });

        if (!campaign) {
          return null;
        }

        const createdTask = await (tx as typeof prismaExtended).generationTask.create({
          data: {
            organizationId,
            campaignId,
            topic,
            targetAudience,
            contentLanguage,
            geoContext,
            outputFormats,
            status: "queued",
          },
        });

        const event = createGenerationRequestedEvent(
          organizationId,
          campaignId,
          createdTask.id,
          topic,
          targetAudience,
          contentLanguage,
          geoContext,
          outputFormats,
        );

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return createdTask;
      });

      if (!task) {
        res.status(404).json({ error: "campaign not found" });
        return;
      }

      res.status(202).json({
        taskId: task.id,
        organizationId: task.organizationId,
        campaignId: task.campaignId,
        contentLanguage: task.contentLanguage,
        geoContext: task.geoContext,
        status: task.status,
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/tasks/:taskId", async (req, res, next) => {
    try {
      const task = await prismaExtended.generationTask.findUnique({
        where: { id: req.params.taskId },
      });

      if (!task) {
        res.status(404).json({ error: "task not found" });
        return;
      }

      const article = await prismaExtended.repositoryArticle.findUnique({
        where: { taskId: task.id },
      });

      res.json({
        id: task.id,
        organizationId: task.organizationId,
        campaignId: task.campaignId,
        topic: task.topic,
        targetAudience: task.targetAudience,
        contentLanguage: task.contentLanguage,
        geoContext: task.geoContext,
        outputFormats: task.outputFormats,
        blueprintId: task.blueprintId,
        blueprint: task.blueprintJson,
        status: task.status,
        completedAt: task.completedAt,
        article: article
          ? {
              id: article.id,
              title: article.title,
              status: article.status,
            }
          : null,
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/tasks/:taskId/status", async (req, res, next) => {
    try {
      const task = await prismaExtended.generationTask.findUnique({
        where: { id: req.params.taskId },
      });

      if (!task) {
        res.status(404).json({ error: "task not found" });
        return;
      }

      const [run, qualifiedTopic, article] = await Promise.all([
        prismaExtended.generationRun.findUnique({
          where: { taskId: task.id },
        }),
        task.qualifiedTopicId
          ? prismaExtended.qualifiedTopic.findUnique({
              where: { id: task.qualifiedTopicId },
            })
          : Promise.resolve(null),
        prismaExtended.repositoryArticle.findUnique({
          where: { taskId: task.id },
        }),
      ]);

      const blueprint = task.blueprintJson as Record<string, any> | null;
      const runState = run?.stateJson as Record<string, any> | undefined;
      const qualificationStatus =
        (qualifiedTopic?.sourceMetadata as Record<string, any> | undefined)?.status ?? null;
      const generationStatus =
        (runState?.statusArtifact as Record<string, any> | undefined) ?? null;

      res.json({
        taskId: task.id,
        topic: task.topic,
        status: task.status,
        statusArtifact: {
          discovery: qualificationStatus?.discovery ?? null,
          qualification: qualificationStatus?.qualification ?? null,
          blueprint: blueprint?.status ?? null,
          generation: generationStatus?.generation ?? null,
          qa: generationStatus?.qa ?? null,
          infra: {
            relay: options.relay?.getStatus() ?? {
              state: "disconnected",
              retryDelayMs: 0,
              retryAt: null,
              connected: false,
            },
          },
        },
        blueprintId: task.blueprintId,
        article: article
          ? {
              id: article.id,
              status: article.status,
              title: article.title,
            }
          : null,
      });
    } catch (error) {
      next(error);
    }
  });

  app.use(
    (
      error: unknown,
      _req: Request,
      res: Response,
      _next: NextFunction,
    ) => {
      console.error(error);
      res.status(500).json({ error: "internal server error" });
    },
  );

  return app;
};
