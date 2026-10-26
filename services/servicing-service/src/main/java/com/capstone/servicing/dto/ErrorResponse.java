package com.capstone.servicing.dto;

import java.time.OffsetDateTime;

public record ErrorResponse(String code, String message, String correlationId, OffsetDateTime timestamp) {
    public static ErrorResponse of(String code, String message, String correlationId) {
        return new ErrorResponse(code, message, correlationId, OffsetDateTime.now());
    }
}
