package com.capstone.servicing.dto;

import java.math.BigDecimal;

/** M8 task 8.4 — served from DynamoDB (MortgageLookup-dev), not PostgreSQL. */
public record MortgageLookupResponse(
        String mortgageExternalId,
        String borrowerExternalId,
        String status,
        BigDecimal outstandingBalance,
        String source
) {
}
