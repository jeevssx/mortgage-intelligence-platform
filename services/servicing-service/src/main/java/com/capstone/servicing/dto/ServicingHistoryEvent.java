package com.capstone.servicing.dto;

import java.time.OffsetDateTime;

public record ServicingHistoryEvent(OffsetDateTime eventTime, String eventType, String description) {
}
