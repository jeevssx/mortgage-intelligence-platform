package com.capstone.servicing.dto;

import java.util.List;

public record ServicingHistoryResponse(String mortgageExternalId, List<ServicingHistoryEvent> events) {
}
