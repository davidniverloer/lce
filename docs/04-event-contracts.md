# Event Contracts

## General Format
All events MUST include:

- eventId (UUID)
- eventType
- timestamp (ISO 8601)
- version
- payload

---

## TopicGenerationRequested

```json
{
  "eventId": "uuid",
  "eventType": "TopicGenerationRequested",
  "version": "1.0",
  "timestamp": "ISO_DATE",
  "payload": {
    "organizationId": "org-123",
    "campaignId": "camp-456",
    "niche": "example niche"
  }
}