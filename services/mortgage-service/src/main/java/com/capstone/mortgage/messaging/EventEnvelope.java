package com.capstone.mortgage.messaging;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * Lifecycle event envelope shared across producers/consumers.
 * Schema: docs/architecture/events/*.schema.json. Catalog: docs/architecture/event-catalog.md.
 */
public record EventEnvelope(
        UUID eventId,
        String eventType,
        OffsetDateTime occurredAt,
        int schemaVersion,
        String correlationId,
        Map<String, Object> payload
) {

    public static EventEnvelope of(String eventType, String correlationId, Map<String, Object> payload) {
        return new EventEnvelope(UUID.randomUUID(), eventType, OffsetDateTime.now(), 1, correlationId, payload);
    }
}
