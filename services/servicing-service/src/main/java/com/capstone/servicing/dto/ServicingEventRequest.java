package com.capstone.servicing.dto;

import jakarta.validation.constraints.NotBlank;

/** Internal event ingestion, e.g. from mortgage-service or a future SNS/SQS consumer (M5). */
public record ServicingEventRequest(
        @NotBlank String eventType,
        String description
) {
}
