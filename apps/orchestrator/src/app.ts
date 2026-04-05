import { randomUUID } from "node:crypto";

import { Prisma } from "@prisma/client";
import express, { type NextFunction, type Request, type Response } from "express";

import {
  CAMPAIGN_CREATED_EVENT_TYPE,
  GENERATION_REQUESTED_EVENT_TYPE,
  INTEGRATION_EVENT_VERSION,
  ORGANIZATION_CREATED_EVENT_TYPE,
  type CampaignCreatedEvent,
  type GenerationRequestedEvent,
  type OrganizationCreatedEvent,
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
  },
});

export const createApp = () => {
  const app = express();
  const prismaPhase2 = prisma as typeof prisma & {
    generationTask: any;
    repositoryArticle: any;
  };

  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
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

        const createdTask = await (tx as typeof prismaPhase2).generationTask.create({
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
      const task = await prismaPhase2.generationTask.findUnique({
        where: { id: req.params.taskId },
      });

      if (!task) {
        res.status(404).json({ error: "task not found" });
        return;
      }

      const article = await prismaPhase2.repositoryArticle.findUnique({
        where: { taskId: task.id },
      });

      res.json({
        id: task.id,
        organizationId: task.organizationId,
        campaignId: task.campaignId,
        topic: task.topic,
        targetAudience: task.targetAudience,
        outputFormats: task.outputFormats,
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
