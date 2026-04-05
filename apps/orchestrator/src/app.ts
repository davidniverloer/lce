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
    outputFormats,
    blueprintId: blueprintId ?? null,
    blueprint: blueprint ?? null,
  },
});

const createTopicGenerationRequestedEvent = (
  organizationId: string,
  campaignId: string,
  analysisRequestId: string,
  seedTopic: string,
  targetAudience: string | null,
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
    targetAudience,
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

export const createApp = () => {
  const app = express();
  const prismaExtended = prisma as typeof prisma & {
    marketAnalysisRequest: any;
    qualifiedTopic: any;
    generationTask: any;
    repositoryArticle: any;
    sitemapIngestion: any;
    indexedPage: any;
    articleBlueprint: any;
    internalLink: any;
  };

  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
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
        qualifiedTopics: topics.map((topic: any) => ({
          id: topic.id,
          topic: topic.topic,
          score: topic.score,
          trendScore: topic.trendScore,
          socialScore: topic.socialScore,
          seoScore: topic.seoScore,
          qualificationNote: topic.qualificationNote,
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
    const targetAudience = getString(req.body?.targetAudience);

    if (!organizationId || !campaignId || !seedTopic) {
      res.status(400).json({
        error: "organizationId, campaignId, and seedTopic are required",
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
            targetAudience,
            status: "queued",
          },
        });

        const event = createTopicGenerationRequestedEvent(
          organizationId,
          campaignId,
          createdRequest.id,
          seedTopic,
          targetAudience,
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

  app.post("/tasks/generate", async (req, res, next) => {
    const organizationId = getString(req.body?.organizationId);
    const campaignId = getString(req.body?.campaignId);
    const topic = getString(req.body?.topic);
    const targetAudience = getString(req.body?.targetAudience);
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
