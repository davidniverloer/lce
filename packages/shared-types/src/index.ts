export type EventEnvelope<TPayload, TType extends string> = {
  eventId: string;
  eventType: TType;
  version: "1.0";
  timestamp: string;
  payload: TPayload;
};

export const ORGANIZATION_CREATED_EVENT_TYPE = "OrganizationCreated";
export const CAMPAIGN_CREATED_EVENT_TYPE = "CampaignCreated";
export const GENERATION_REQUESTED_EVENT_TYPE = "GenerationRequested";
export const TOPIC_GENERATION_REQUESTED_EVENT_TYPE = "TopicGenerationRequested";
export const TOPIC_QUALIFIED_EVENT_TYPE = "TopicQualified";
export const SITEMAP_UPDATED_EVENT_TYPE = "SitemapUpdated";
export const BLUEPRINT_VALIDATED_EVENT_TYPE = "BlueprintValidated";
export const INTEGRATION_EVENT_VERSION = "1.0" as const;

export type OrganizationCreatedPayload = {
  organizationId: string;
  name: string;
};

export type CampaignCreatedPayload = {
  organizationId: string;
  campaignId: string;
  name: string;
};

export type GenerationRequestedPayload = {
  organizationId: string;
  campaignId: string;
  taskId: string;
  topic: string;
  targetAudience: string | null;
  contentLanguage: string | null;
  geoContext: string | null;
  outputFormats: string[];
  blueprintId?: string | null;
  blueprint?: ArticleBlueprintSnapshot | null;
};

export type ArticleBlueprintSnapshot = {
  topic: string;
  targetAudience: string | null;
  contentLanguage?: string | null;
  geoContext?: string | null;
  angle: string;
  sections: string[];
  styleGuidance: string;
  differentiationAngle?: string;
  differentiationRationale?: string;
  targetDelta?: string;
  audienceShift?: string | null;
  siteContext?: Record<string, unknown>;
  status?: Record<string, unknown>;
  internalLinks: InternalLinkSnapshot[];
};

export type InternalLinkSnapshot = {
  url: string;
  title: string;
  anchorText: string;
  rationale: string;
  pageSummary?: string;
  pageRole?: string;
  topicCluster?: string;
  relevanceScore?: number;
  placementHint?: string;
};

export type TopicGenerationRequestedPayload = {
  organizationId: string;
  campaignId: string;
  analysisRequestId: string;
  seedTopic: string | null;
  industry?: string | null;
  autoDiscover?: boolean;
  targetAudience: string | null;
  contentLanguage: string | null;
  geoContext: string | null;
};

export type TopicQualifiedPayload = {
  organizationId: string;
  campaignId: string;
  analysisRequestId: string;
  qualifiedTopicId: string;
  topic: string;
  score: number;
  targetAudience: string | null;
};

export type SitemapUpdatedPayload = {
  organizationId: string;
  campaignId: string;
  sitemapIngestionId: string;
  sitemapUrl: string;
  indexedPageCount: number;
};

export type BlueprintValidatedPayload = {
  organizationId: string;
  campaignId: string;
  qualifiedTopicId: string;
  sitemapIngestionId: string;
  blueprintId: string;
};

export type OrganizationCreatedEvent = EventEnvelope<
  OrganizationCreatedPayload,
  typeof ORGANIZATION_CREATED_EVENT_TYPE
>;

export type CampaignCreatedEvent = EventEnvelope<
  CampaignCreatedPayload,
  typeof CAMPAIGN_CREATED_EVENT_TYPE
>;

export type GenerationRequestedEvent = EventEnvelope<
  GenerationRequestedPayload,
  typeof GENERATION_REQUESTED_EVENT_TYPE
>;

export type TopicGenerationRequestedEvent = EventEnvelope<
  TopicGenerationRequestedPayload,
  typeof TOPIC_GENERATION_REQUESTED_EVENT_TYPE
>;

export type TopicQualifiedEvent = EventEnvelope<
  TopicQualifiedPayload,
  typeof TOPIC_QUALIFIED_EVENT_TYPE
>;

export type SitemapUpdatedEvent = EventEnvelope<
  SitemapUpdatedPayload,
  typeof SITEMAP_UPDATED_EVENT_TYPE
>;

export type BlueprintValidatedEvent = EventEnvelope<
  BlueprintValidatedPayload,
  typeof BLUEPRINT_VALIDATED_EVENT_TYPE
>;

export type IntegrationEvent =
  | OrganizationCreatedEvent
  | CampaignCreatedEvent
  | GenerationRequestedEvent
  | TopicGenerationRequestedEvent
  | TopicQualifiedEvent
  | SitemapUpdatedEvent
  | BlueprintValidatedEvent;

export const isOrganizationCreatedEvent = (
  value: unknown,
): value is OrganizationCreatedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === ORGANIZATION_CREATED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.name === "string"
  );
};

export const isCampaignCreatedEvent = (
  value: unknown,
): value is CampaignCreatedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === CAMPAIGN_CREATED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.name === "string"
  );
};

export const isGenerationRequestedEvent = (
  value: unknown,
): value is GenerationRequestedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === GENERATION_REQUESTED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.taskId === "string" &&
    typeof payload.topic === "string" &&
    (typeof payload.targetAudience === "string" || payload.targetAudience === null) &&
    (typeof payload.contentLanguage === "string" ||
      payload.contentLanguage === null) &&
    (typeof payload.geoContext === "string" || payload.geoContext === null) &&
    Array.isArray(payload.outputFormats) &&
    payload.outputFormats.every((value) => typeof value === "string") &&
    (payload.blueprintId === undefined ||
      payload.blueprintId === null ||
      typeof payload.blueprintId === "string") &&
    (payload.blueprint === undefined ||
      payload.blueprint === null ||
      isArticleBlueprintSnapshot(payload.blueprint))
  );
};

export const isTopicGenerationRequestedEvent = (
  value: unknown,
): value is TopicGenerationRequestedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === TOPIC_GENERATION_REQUESTED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.analysisRequestId === "string" &&
    (typeof payload.seedTopic === "string" || payload.seedTopic === null) &&
    (payload.industry === undefined ||
      payload.industry === null ||
      typeof payload.industry === "string") &&
    (payload.autoDiscover === undefined || typeof payload.autoDiscover === "boolean") &&
    (typeof payload.targetAudience === "string" || payload.targetAudience === null) &&
    (typeof payload.contentLanguage === "string" ||
      payload.contentLanguage === null) &&
    (typeof payload.geoContext === "string" || payload.geoContext === null)
  );
};

export const isTopicQualifiedEvent = (value: unknown): value is TopicQualifiedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === TOPIC_QUALIFIED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.analysisRequestId === "string" &&
    typeof payload.qualifiedTopicId === "string" &&
    typeof payload.topic === "string" &&
    typeof payload.score === "number" &&
    (typeof payload.targetAudience === "string" || payload.targetAudience === null)
  );
};

export const isSitemapUpdatedEvent = (value: unknown): value is SitemapUpdatedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === SITEMAP_UPDATED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.sitemapIngestionId === "string" &&
    typeof payload.sitemapUrl === "string" &&
    typeof payload.indexedPageCount === "number"
  );
};

export const isBlueprintValidatedEvent = (
  value: unknown,
): value is BlueprintValidatedEvent => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const payload = candidate.payload as Record<string, unknown> | undefined;

  return (
    typeof candidate.eventId === "string" &&
    candidate.eventType === BLUEPRINT_VALIDATED_EVENT_TYPE &&
    candidate.version === INTEGRATION_EVENT_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.qualifiedTopicId === "string" &&
    typeof payload.sitemapIngestionId === "string" &&
    typeof payload.blueprintId === "string"
  );
};

const isInternalLinkSnapshot = (value: unknown): value is InternalLinkSnapshot => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.url === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.anchorText === "string" &&
    typeof candidate.rationale === "string"
  );
};

const isArticleBlueprintSnapshot = (
  value: unknown,
): value is ArticleBlueprintSnapshot => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.topic === "string" &&
    (typeof candidate.targetAudience === "string" ||
      candidate.targetAudience === null) &&
    (typeof candidate.contentLanguage === "string" ||
      candidate.contentLanguage === undefined ||
      candidate.contentLanguage === null) &&
    (typeof candidate.geoContext === "string" ||
      candidate.geoContext === undefined ||
      candidate.geoContext === null) &&
    typeof candidate.angle === "string" &&
    typeof candidate.styleGuidance === "string" &&
    Array.isArray(candidate.sections) &&
    candidate.sections.every((item) => typeof item === "string") &&
    Array.isArray(candidate.internalLinks) &&
    candidate.internalLinks.every(isInternalLinkSnapshot)
  );
};
