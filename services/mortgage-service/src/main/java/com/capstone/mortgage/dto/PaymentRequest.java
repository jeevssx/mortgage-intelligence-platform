package com.capstone.mortgage.dto;

import com.capstone.mortgage.entity.PaymentStatus;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDate;

public record PaymentRequest(

        @NotNull LocalDate dueDate,

        LocalDate paidDate,

        @NotNull @DecimalMin(value = "0.0", inclusive = false)
        java.math.BigDecimal amount,

        @NotNull PaymentStatus status
) {
}
