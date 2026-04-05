import { randomUUID } from "node:crypto";

import { Prisma } from "@prisma/client";
import express, { type NextFunction, type Request, type Response } from "express";

import {
  CAMPAIGN_CREATED_EVENT_TYPE,
  INTEGRATION_EVENT_VERSION,
  ORGANIZATION_CREATED_EVENT_TYPE,
  type CampaignCreatedEvent,
  type OrganizationCreatedEvent,
} from "@lce/shared-types";

import { prisma } from "./db";

const getString = (value: unknown): string | null =>
  typeof value === "string" && value.trim().length > 0 ? value.trim() : null;

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

export const createApp = () => {
  const app = express();

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
