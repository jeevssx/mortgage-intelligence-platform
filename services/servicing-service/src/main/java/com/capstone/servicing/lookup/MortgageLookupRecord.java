package com.capstone.servicing.lookup;

import java.math.BigDecimal;

/** One item in the DynamoDB MortgageLookup-dev table (M8 task 8.4). */
public record MortgageLookupRecord(
        String mortgageExternalId,
        String borrowerExternalId,
        String status,
        BigDecimal outstandingBalance
) {
}
