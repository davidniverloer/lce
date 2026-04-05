export const TOPIC_GENERATION_REQUESTED_EVENT_TYPE = "TopicGenerationRequested";
export const TOPIC_GENERATION_REQUESTED_VERSION = "1.0";

export type EventEnvelope<TPayload> = {
  eventId: string;
  eventType: string;
  version: string;
  timestamp: string;
  payload: TPayload;
};

export type TopicGenerationRequestedPayload = {
  organizationId: string;
  campaignId: string;
  niche: string;
};

export type TopicGenerationRequestedEvent = EventEnvelope<TopicGenerationRequestedPayload> & {
  eventType: typeof TOPIC_GENERATION_REQUESTED_EVENT_TYPE;
  version: typeof TOPIC_GENERATION_REQUESTED_VERSION;
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
    candidate.version === TOPIC_GENERATION_REQUESTED_VERSION &&
    typeof candidate.timestamp === "string" &&
    typeof payload?.organizationId === "string" &&
    typeof payload.campaignId === "string" &&
    typeof payload.niche === "string"
  );
};
