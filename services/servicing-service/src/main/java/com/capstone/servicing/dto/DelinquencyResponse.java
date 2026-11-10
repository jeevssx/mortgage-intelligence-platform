package com.capstone.servicing.dto;

import java.time.LocalDate;

public record DelinquencyResponse(
        String mortgageExternalId,
        String status,
        LocalDate delinquentSince,
        Integer daysPastDue,
        String severity
) {
}
