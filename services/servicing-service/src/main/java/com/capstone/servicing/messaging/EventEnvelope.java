package com.capstone.servicing.messaging;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

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
