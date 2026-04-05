export type EventEnvelope<TPayload, TType extends string> = {
  eventId: string;
  eventType: TType;
  version: "1.0";
  timestamp: string;
  payload: TPayload;
};

export const ORGANIZATION_CREATED_EVENT_TYPE = "OrganizationCreated";
export const CAMPAIGN_CREATED_EVENT_TYPE = "CampaignCreated";
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

export type OrganizationCreatedEvent = EventEnvelope<
  OrganizationCreatedPayload,
  typeof ORGANIZATION_CREATED_EVENT_TYPE
>;

export type CampaignCreatedEvent = EventEnvelope<
  CampaignCreatedPayload,
  typeof CAMPAIGN_CREATED_EVENT_TYPE
>;

export type IntegrationEvent = OrganizationCreatedEvent | CampaignCreatedEvent;

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
