import { randomUUID } from "node:crypto";

import { Prisma } from "@prisma/client";
import express, { type NextFunction, type Request, type Response } from "express";

import {
  TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
  TOPIC_GENERATION_REQUESTED_VERSION,
  type TopicGenerationRequestedEvent,
} from "@lce/shared-types";

import { prisma } from "./db";

const requireOrganizationId = (req: Request, res: Response): string | null => {
  const organizationId = req.header("x-organization-id");
  if (!organizationId) {
    res.status(400).json({ error: "x-organization-id header is required" });
    return null;
  }
  return organizationId;
};

const getString = (value: unknown): string | null =>
  typeof value === "string" && value.trim().length > 0 ? value.trim() : null;

export const createApp = () => {
  const app = express();

  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/campaigns", async (req, res, next) => {
    const organizationId = requireOrganizationId(req, res);
    if (!organizationId) {
      return;
    }

    const name = getString(req.body?.name);
    const niche = getString(req.body?.niche);

    if (!name || !niche) {
      res.status(400).json({ error: "name and niche are required" });
      return;
    }

    try {
      const campaign = await prisma.campaign.create({
        data: {
          organizationId,
          name,
          niche,
        },
      });

      res.status(201).json({
        id: campaign.id,
        organizationId: campaign.organizationId,
        name: campaign.name,
        niche: campaign.niche,
        createdAt: campaign.createdAt,
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/campaigns/:id/topic-generation", async (req, res, next) => {
    const organizationId = requireOrganizationId(req, res);
    if (!organizationId) {
      return;
    }

    try {
      const campaign = await prisma.$transaction(async (tx) => {
        const existingCampaign = await tx.campaign.findFirst({
          where: {
            id: req.params.id,
            organizationId,
          },
        });

        if (!existingCampaign) {
          return null;
        }

        const event: TopicGenerationRequestedEvent = {
          eventId: randomUUID(),
          eventType: TOPIC_GENERATION_REQUESTED_EVENT_TYPE,
          version: TOPIC_GENERATION_REQUESTED_VERSION,
          timestamp: new Date().toISOString(),
          payload: {
            organizationId,
            campaignId: existingCampaign.id,
            niche: existingCampaign.niche,
          },
        };

        await tx.outboxEvent.create({
          data: {
            id: event.eventId,
            organizationId,
            eventType: event.eventType,
            payload: event as Prisma.InputJsonValue,
          },
        });

        return existingCampaign;
      });

      if (!campaign) {
        res.status(404).json({ error: "campaign not found" });
        return;
      }

      res.status(202).json({
        campaignId: campaign.id,
        status: "queued",
      });
    } catch (error) {
      next(error);
    }
  });

  app.get("/campaigns/:id/topics", async (req, res, next) => {
    const organizationId = requireOrganizationId(req, res);
    if (!organizationId) {
      return;
    }

    try {
      const campaign = await prisma.campaign.findFirst({
        where: {
          id: req.params.id,
          organizationId,
        },
      });

      if (!campaign) {
        res.status(404).json({ error: "campaign not found" });
        return;
      }

      const topics = await prisma.topic.findMany({
        where: {
          organizationId,
          campaignId: campaign.id,
        },
        orderBy: {
          createdAt: "asc",
        },
      });

      res.json({
        campaignId: campaign.id,
        topics: topics.map((topic) => ({
          id: topic.id,
          title: topic.title,
          createdAt: topic.createdAt,
        })),
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
