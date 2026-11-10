package com.capstone.mortgage.dto;

import com.capstone.mortgage.entity.PaymentStatus;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record PaymentResponse(
        UUID id,
        String mortgageExternalId,
        LocalDate dueDate,
        LocalDate paidDate,
        BigDecimal amount,
        PaymentStatus status,
        BigDecimal outstandingBalanceAfter
) {
}
