import assert from "node:assert/strict";
import test from "node:test";

import { createApp } from "./app";
import { prisma } from "./db";

test("GET /tasks/:taskId/status returns the Phase 3.5 status contract", async () => {
  const prismaAny = prisma as Record<string, any>;
  const generationTaskDelegate = prismaAny.generationTask;
  const generationRunDelegate = prismaAny.generationRun;
  const qualifiedTopicDelegate = prismaAny.qualifiedTopic;
  const repositoryArticleDelegate = prismaAny.repositoryArticle;

  const originalGenerationTaskFindUnique = generationTaskDelegate.findUnique;
  const originalGenerationRunFindUnique = generationRunDelegate.findUnique;
  const originalQualifiedTopicFindUnique = qualifiedTopicDelegate.findUnique;
  const originalRepositoryArticleFindUnique = repositoryArticleDelegate.findUnique;

  generationTaskDelegate.findUnique = async () => ({
    id: "task-123",
    topic: "ambient AI scribes in healthcare",
    status: "completed",
    blueprintId: "blueprint-123",
    qualifiedTopicId: "qualified-topic-123",
    blueprintJson: {
      status: {
        blueprintReady: true,
        differentiationReady: true,
        sitemapUsed: true,
        internalLinkCount: 3,
        siteAware: true,
      },
    },
  });

  generationRunDelegate.findUnique = async () => ({
    stateJson: {
      statusArtifact: {
        generation: {
          status: "completed",
          qaPassed: true,
          qaStatus: "pass",
          revisionNumber: 1,
          maxRevisionAttempts: 1,
        },
        qa: {
          passed: true,
          issues: [],
          revisionInstructions: [],
          rubric: {
            structureCompleteness: "pass",
            blueprintFidelity: "pass",
            differentiationAdherence: "pass",
            audienceLanguageGeoFit: "pass",
            internalLinkingQuality: "pass",
            clarityAndCoherence: "pass",
          },
          feedback: "Draft passes the expanded QA and compliance checks.",
        },
      },
    },
  });

  qualifiedTopicDelegate.findUnique = async () => ({
    sourceMetadata: {
      status: {
        discovery: {
          mode: "mixed",
          sources: ["news", "seo"],
          sourceConfidence: 0.81,
        },
        qualification: {
          mode: "mixed",
          fallbackCount: 1,
          providerModes: {
            seo: "mixed",
            trend: "live",
            social: "stub",
          },
          weightedScore: 84.2,
          confidenceBand: "medium",
          confidenceScore: 0.76,
          fallbackWeightShare: 0.2,
          qualificationStatus: "qualified",
        },
      },
    },
  });

  repositoryArticleDelegate.findUnique = async () => ({
    id: "article-123",
    status: "completed",
    title: "ambient AI scribes in healthcare: Practical Guide",
  });

  const app = createApp({
    relay: {
      getStatus: () => ({
        state: "ready",
        retryDelayMs: 1000,
        retryAt: null,
        connected: true,
      }),
    } as any,
  });

  try {
    const routeLayer = (app as any)._router.stack.find(
      (layer: any) =>
        layer.route?.path === "/tasks/:taskId/status" &&
        layer.route?.methods?.get === true,
    );
    assert.ok(routeLayer, "Expected /tasks/:taskId/status route to be registered.");

    const handler = routeLayer.route.stack.at(-1)?.handle as
      | ((
          req: Record<string, any>,
          res: Record<string, any>,
          next: (error?: unknown) => void,
        ) => Promise<void>)
      | undefined;
    assert.ok(handler, "Expected /tasks/:taskId/status to have a route handler.");

    const req = {
      params: { taskId: "task-123" },
    };

    let statusCode = 200;
    let payload: Record<string, any> | undefined;
    const res = {
      status(code: number) {
        statusCode = code;
        return this;
      },
      json(body: Record<string, any>) {
        payload = body;
        return this;
      },
    };

    await handler(req, res, (error?: unknown) => {
      if (error) {
        throw error;
      }
    });

    assert.equal(statusCode, 200);
    assert.ok(payload, "Expected /tasks/:taskId/status to return a JSON payload.");
    assert.equal(payload.taskId, "task-123");
    assert.equal(payload.topic, "ambient AI scribes in healthcare");
    assert.equal(payload.status, "completed");
    assert.equal(payload.blueprintId, "blueprint-123");
    assert.deepEqual(payload.article, {
      id: "article-123",
      status: "completed",
      title: "ambient AI scribes in healthcare: Practical Guide",
    });

    assert.deepEqual(payload.statusArtifact.discovery, {
      mode: "mixed",
      sources: ["news", "seo"],
      sourceConfidence: 0.81,
    });
    assert.deepEqual(payload.statusArtifact.qualification, {
      mode: "mixed",
      fallbackCount: 1,
      providerModes: {
        seo: "mixed",
        trend: "live",
        social: "stub",
      },
      weightedScore: 84.2,
      confidenceBand: "medium",
      confidenceScore: 0.76,
      fallbackWeightShare: 0.2,
      qualificationStatus: "qualified",
    });
    assert.deepEqual(payload.statusArtifact.blueprint, {
      blueprintReady: true,
      differentiationReady: true,
      sitemapUsed: true,
      internalLinkCount: 3,
      siteAware: true,
    });
    assert.deepEqual(payload.statusArtifact.generation, {
      status: "completed",
      qaPassed: true,
      qaStatus: "pass",
      revisionNumber: 1,
      maxRevisionAttempts: 1,
    });
    assert.deepEqual(payload.statusArtifact.qa, {
      passed: true,
      issues: [],
      revisionInstructions: [],
      rubric: {
        structureCompleteness: "pass",
        blueprintFidelity: "pass",
        differentiationAdherence: "pass",
        audienceLanguageGeoFit: "pass",
        internalLinkingQuality: "pass",
        clarityAndCoherence: "pass",
      },
      feedback: "Draft passes the expanded QA and compliance checks.",
    });
    assert.deepEqual(payload.statusArtifact.infra.relay, {
      state: "ready",
      retryDelayMs: 1000,
      retryAt: null,
      connected: true,
    });
  } finally {
    generationTaskDelegate.findUnique = originalGenerationTaskFindUnique;
    generationRunDelegate.findUnique = originalGenerationRunFindUnique;
    qualifiedTopicDelegate.findUnique = originalQualifiedTopicFindUnique;
    repositoryArticleDelegate.findUnique = originalRepositoryArticleFindUnique;
  }
});

test("GET /campaigns/:campaignId/status-summary returns compact Phase 3.5 summaries", async () => {
  const prismaAny = prisma as Record<string, any>;
  const generationTaskDelegate = prismaAny.generationTask;
  const generationRunDelegate = prismaAny.generationRun;
  const qualifiedTopicDelegate = prismaAny.qualifiedTopic;
  const repositoryArticleDelegate = prismaAny.repositoryArticle;

  const originalGenerationTaskFindMany = generationTaskDelegate.findMany;
  const originalGenerationRunFindMany = generationRunDelegate.findMany;
  const originalQualifiedTopicFindMany = qualifiedTopicDelegate.findMany;
  const originalRepositoryArticleFindMany = repositoryArticleDelegate.findMany;

  generationTaskDelegate.findMany = async () => [
    {
      id: "task-123",
      topic: "ambient AI scribes in healthcare",
      status: "completed",
      qualifiedTopicId: "qualified-topic-123",
      blueprintJson: {
        status: {
          differentiationReady: true,
          sitemapUsed: true,
          siteAware: true,
        },
      },
    },
  ];

  generationRunDelegate.findMany = async () => [
    {
      taskId: "task-123",
      stateJson: {
        statusArtifact: {
          generation: {
            qaStatus: "pass",
            qaPassed: true,
          },
        },
      },
    },
  ];

  qualifiedTopicDelegate.findMany = async () => [
    {
      id: "qualified-topic-123",
      sourceMetadata: {
        status: {
          discovery: {
            mode: "mixed",
            sources: ["news", "seo"],
          },
          qualification: {
            confidenceScore: 0.76,
            confidenceBand: "medium",
            fallbackWeightShare: 0.2,
            fallbackCount: 1,
          },
        },
      },
    },
  ];

  repositoryArticleDelegate.findMany = async () => [
    {
      id: "article-123",
      taskId: "task-123",
      status: "completed",
    },
  ];

  const app = createApp();

  try {
    const routeLayer = (app as any)._router.stack.find(
      (layer: any) =>
        layer.route?.path === "/campaigns/:campaignId/status-summary" &&
        layer.route?.methods?.get === true,
    );
    assert.ok(
      routeLayer,
      "Expected /campaigns/:campaignId/status-summary route to be registered.",
    );

    const handler = routeLayer.route.stack.at(-1)?.handle as
      | ((
          req: Record<string, any>,
          res: Record<string, any>,
          next: (error?: unknown) => void,
        ) => Promise<void>)
      | undefined;
    assert.ok(
      handler,
      "Expected /campaigns/:campaignId/status-summary to have a route handler.",
    );

    const req = {
      params: { campaignId: "campaign-123" },
      query: { organizationId: "org-123" },
    };

    let statusCode = 200;
    let payload: Record<string, any> | undefined;
    const res = {
      status(code: number) {
        statusCode = code;
        return this;
      },
      json(body: Record<string, any>) {
        payload = body;
        return this;
      },
    };

    await handler(req, res, (error?: unknown) => {
      if (error) {
        throw error;
      }
    });

    assert.equal(statusCode, 200);
    assert.deepEqual(payload, {
      organizationId: "org-123",
      campaignId: "campaign-123",
      summaries: [
        {
          taskId: "task-123",
          topic: "ambient AI scribes in healthcare",
          taskStatus: "completed",
          articleStatus: "completed",
          articleId: "article-123",
          confidenceScore: 0.76,
          confidenceBand: "medium",
          fallbackWeightShare: 0.2,
          fallbackCount: 1,
          discoveryMode: "mixed",
          discoverySources: ["news", "seo"],
          differentiationReady: true,
          sitemapUsed: true,
          siteAware: true,
          qaStatus: "pass",
          qaPassed: true,
        },
      ],
    });
  } finally {
    generationTaskDelegate.findMany = originalGenerationTaskFindMany;
    generationRunDelegate.findMany = originalGenerationRunFindMany;
    qualifiedTopicDelegate.findMany = originalQualifiedTopicFindMany;
    repositoryArticleDelegate.findMany = originalRepositoryArticleFindMany;
  }
});

test("GET /campaigns/:campaignId/status-trends returns compact Phase 3.5 aggregates", async () => {
  const prismaAny = prisma as Record<string, any>;
  const generationTaskDelegate = prismaAny.generationTask;
  const generationRunDelegate = prismaAny.generationRun;
  const qualifiedTopicDelegate = prismaAny.qualifiedTopic;
  const repositoryArticleDelegate = prismaAny.repositoryArticle;

  const originalGenerationTaskFindMany = generationTaskDelegate.findMany;
  const originalGenerationRunFindMany = generationRunDelegate.findMany;
  const originalQualifiedTopicFindMany = qualifiedTopicDelegate.findMany;
  const originalRepositoryArticleFindMany = repositoryArticleDelegate.findMany;

  generationTaskDelegate.findMany = async () => [
    {
      id: "task-123",
      topic: "ambient AI scribes in healthcare",
      status: "completed",
      qualifiedTopicId: "qualified-topic-123",
      blueprintJson: {
        status: {
          differentiationReady: true,
          siteAware: true,
        },
      },
    },
    {
      id: "task-456",
      topic: "nurse staffing analytics",
      status: "processing",
      qualifiedTopicId: "qualified-topic-456",
      blueprintJson: {
        status: {
          differentiationReady: false,
          siteAware: false,
        },
      },
    },
  ];

  generationRunDelegate.findMany = async () => [
    {
      taskId: "task-123",
      stateJson: {
        statusArtifact: {
          generation: {
            qaPassed: true,
          },
        },
      },
    },
    {
      taskId: "task-456",
      stateJson: {
        statusArtifact: {
          generation: {
            qaPassed: false,
          },
        },
      },
    },
  ];

  qualifiedTopicDelegate.findMany = async () => [
    {
      id: "qualified-topic-123",
      sourceMetadata: {
        status: {
          discovery: {
            sources: ["news", "seo"],
          },
          qualification: {
            confidenceScore: 0.8,
            fallbackWeightShare: 0.1,
          },
        },
      },
    },
    {
      id: "qualified-topic-456",
      sourceMetadata: {
        status: {
          discovery: {
            sources: ["news", "social"],
          },
          qualification: {
            confidenceScore: 0.6,
            fallbackWeightShare: 0.3,
          },
        },
      },
    },
  ];

  repositoryArticleDelegate.findMany = async () => [
    {
      id: "article-123",
      taskId: "task-123",
      status: "completed",
    },
  ];

  const app = createApp();

  try {
    const routeLayer = (app as any)._router.stack.find(
      (layer: any) =>
        layer.route?.path === "/campaigns/:campaignId/status-trends" &&
        layer.route?.methods?.get === true,
    );
    assert.ok(
      routeLayer,
      "Expected /campaigns/:campaignId/status-trends route to be registered.",
    );

    const handler = routeLayer.route.stack.at(-1)?.handle as
      | ((
          req: Record<string, any>,
          res: Record<string, any>,
          next: (error?: unknown) => void,
        ) => Promise<void>)
      | undefined;
    assert.ok(
      handler,
      "Expected /campaigns/:campaignId/status-trends to have a route handler.",
    );

    const req = {
      params: { campaignId: "campaign-123" },
      query: { organizationId: "org-123" },
    };

    let statusCode = 200;
    let payload: Record<string, any> | undefined;
    const res = {
      status(code: number) {
        statusCode = code;
        return this;
      },
      json(body: Record<string, any>) {
        payload = body;
        return this;
      },
    };

    await handler(req, res, (error?: unknown) => {
      if (error) {
        throw error;
      }
    });

    assert.equal(statusCode, 200);
    assert.deepEqual(payload, {
      organizationId: "org-123",
      campaignId: "campaign-123",
      metrics: {
        totalTasks: 2,
        taskStatusCounts: {
          completed: 1,
          processing: 1,
        },
        articleCompletedCount: 1,
        averageConfidenceScore: 0.7,
        averageFallbackWeightShare: 0.2,
        differentiationReadyCount: 1,
        siteAwareCount: 1,
        qaPassCount: 1,
        qaPassRate: 0.5,
        topDiscoverySources: [
          { source: "news", count: 2 },
          { source: "seo", count: 1 },
          { source: "social", count: 1 },
        ],
      },
    });
  } finally {
    generationTaskDelegate.findMany = originalGenerationTaskFindMany;
    generationRunDelegate.findMany = originalGenerationRunFindMany;
    qualifiedTopicDelegate.findMany = originalQualifiedTopicFindMany;
    repositoryArticleDelegate.findMany = originalRepositoryArticleFindMany;
  }
});

test("GET /campaigns/:campaignId/status-compare returns recent-window Phase 3.5 deltas", async () => {
  const prismaAny = prisma as Record<string, any>;
  const generationTaskDelegate = prismaAny.generationTask;
  const generationRunDelegate = prismaAny.generationRun;
  const qualifiedTopicDelegate = prismaAny.qualifiedTopic;
  const repositoryArticleDelegate = prismaAny.repositoryArticle;

  const originalGenerationTaskFindMany = generationTaskDelegate.findMany;
  const originalGenerationRunFindMany = generationRunDelegate.findMany;
  const originalQualifiedTopicFindMany = qualifiedTopicDelegate.findMany;
  const originalRepositoryArticleFindMany = repositoryArticleDelegate.findMany;

  generationTaskDelegate.findMany = async () => [
    {
      id: "task-1",
      qualifiedTopicId: "qualified-topic-1",
      blueprintJson: { status: { differentiationReady: true, siteAware: true } },
    },
    {
      id: "task-2",
      qualifiedTopicId: "qualified-topic-2",
      blueprintJson: { status: { differentiationReady: true, siteAware: false } },
    },
    {
      id: "task-3",
      qualifiedTopicId: "qualified-topic-3",
      blueprintJson: { status: { differentiationReady: false, siteAware: true } },
    },
    {
      id: "task-4",
      qualifiedTopicId: "qualified-topic-4",
      blueprintJson: { status: { differentiationReady: false, siteAware: false } },
    },
  ];

  generationRunDelegate.findMany = async () => [
    { taskId: "task-1", stateJson: { statusArtifact: { generation: { qaPassed: true } } } },
    { taskId: "task-2", stateJson: { statusArtifact: { generation: { qaPassed: true } } } },
    { taskId: "task-3", stateJson: { statusArtifact: { generation: { qaPassed: false } } } },
    { taskId: "task-4", stateJson: { statusArtifact: { generation: { qaPassed: false } } } },
  ];

  qualifiedTopicDelegate.findMany = async () => [
    {
      id: "qualified-topic-1",
      sourceMetadata: { status: { discovery: { sources: ["news", "seo"] }, qualification: { confidenceScore: 0.9, fallbackWeightShare: 0.1 } } },
    },
    {
      id: "qualified-topic-2",
      sourceMetadata: { status: { discovery: { sources: ["news"] }, qualification: { confidenceScore: 0.7, fallbackWeightShare: 0.2 } } },
    },
    {
      id: "qualified-topic-3",
      sourceMetadata: { status: { discovery: { sources: ["social"] }, qualification: { confidenceScore: 0.5, fallbackWeightShare: 0.3 } } },
    },
    {
      id: "qualified-topic-4",
      sourceMetadata: { status: { discovery: { sources: ["seo"] }, qualification: { confidenceScore: 0.3, fallbackWeightShare: 0.4 } } },
    },
  ];

  repositoryArticleDelegate.findMany = async () => [
    { taskId: "task-1", status: "completed" },
    { taskId: "task-2", status: "completed" },
  ];

  const app = createApp();

  try {
    const routeLayer = (app as any)._router.stack.find(
      (layer: any) =>
        layer.route?.path === "/campaigns/:campaignId/status-compare" &&
        layer.route?.methods?.get === true,
    );
    assert.ok(
      routeLayer,
      "Expected /campaigns/:campaignId/status-compare route to be registered.",
    );

    const handler = routeLayer.route.stack.at(-1)?.handle as
      | ((
          req: Record<string, any>,
          res: Record<string, any>,
          next: (error?: unknown) => void,
        ) => Promise<void>)
      | undefined;
    assert.ok(
      handler,
      "Expected /campaigns/:campaignId/status-compare to have a route handler.",
    );

    const req = {
      params: { campaignId: "campaign-123" },
      query: { organizationId: "org-123", window: "2" },
    };

    let statusCode = 200;
    let payload: Record<string, any> | undefined;
    const res = {
      status(code: number) {
        statusCode = code;
        return this;
      },
      json(body: Record<string, any>) {
        payload = body;
        return this;
      },
    };

    await handler(req, res, (error?: unknown) => {
      if (error) {
        throw error;
      }
    });

    assert.equal(statusCode, 200);
    assert.deepEqual(payload, {
      organizationId: "org-123",
      campaignId: "campaign-123",
      windowSize: 2,
      latest: {
        taskCount: 2,
        articleCompletedCount: 2,
        averageConfidenceScore: 0.8,
        averageFallbackWeightShare: 0.15000000000000002,
        differentiationReadyRate: 1,
        siteAwareRate: 0.5,
        qaPassRate: 1,
        topDiscoverySources: [
          { source: "news", count: 2 },
          { source: "seo", count: 1 },
        ],
      },
      previous: {
        taskCount: 2,
        articleCompletedCount: 0,
        averageConfidenceScore: 0.4,
        averageFallbackWeightShare: 0.35,
        differentiationReadyRate: 0,
        siteAwareRate: 0.5,
        qaPassRate: 0,
        topDiscoverySources: [
          { source: "seo", count: 1 },
          { source: "social", count: 1 },
        ],
      },
      delta: {
        averageConfidenceScoreChange: 0.4,
        averageFallbackWeightShareChange: -0.19999999999999996,
        qaPassRateChange: 1,
        differentiationReadyRateChange: 1,
        siteAwareRateChange: 0,
        discoverySourceCountChange: [
          { source: "news", countChange: 2 },
          { source: "seo", countChange: 0 },
        ],
      },
    });
  } finally {
    generationTaskDelegate.findMany = originalGenerationTaskFindMany;
    generationRunDelegate.findMany = originalGenerationRunFindMany;
    qualifiedTopicDelegate.findMany = originalQualifiedTopicFindMany;
    repositoryArticleDelegate.findMany = originalRepositoryArticleFindMany;
  }
});
