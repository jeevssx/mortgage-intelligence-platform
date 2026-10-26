package com.capstone.mortgage.dto;

import com.capstone.mortgage.entity.MortgageStatus;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record MortgageResponse(
        UUID id,
        String mortgageExternalId,
        String borrowerExternalId,
        MortgageStatus status,
        BigDecimal originalAmount,
        BigDecimal outstandingBalance,
        LocalDate originationDate,
        LoanResponse loan
) {
}
