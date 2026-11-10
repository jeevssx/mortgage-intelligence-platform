package com.capstone.mortgage.dto;

import com.capstone.mortgage.entity.UnderwritingDecision;

import java.math.BigDecimal;
import java.util.UUID;

public record LoanResponse(
        UUID id,
        String loanExternalId,
        BigDecimal interestRate,
        Integer termMonths,
        UnderwritingDecision underwritingDecision
) {
}
