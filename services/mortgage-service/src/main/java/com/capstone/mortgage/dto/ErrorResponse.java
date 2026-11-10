package com.capstone.mortgage.dto;

import java.time.OffsetDateTime;

/** Standard error envelope shared across Java/Python services. See guides/standards.md. */
public record ErrorResponse(String code, String message, String correlationId, OffsetDateTime timestamp) {

    public static ErrorResponse of(String code, String message, String correlationId) {
        return new ErrorResponse(code, message, correlationId, OffsetDateTime.now());
    }
}
