package com.capstone.mortgage.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.time.LocalDate;

public record MortgageRequest(

        @NotBlank @Pattern(regexp = "^MTG-[0-9]{4}$", message = "must match MTG-####")
        String mortgageExternalId,

        @NotBlank @Pattern(regexp = "^BOR-[0-9]{3}$", message = "must match BOR-###")
        String borrowerExternalId,

        @NotNull @DecimalMin(value = "0.0", inclusive = false)
        BigDecimal originalAmount,

        @NotNull @DecimalMin(value = "0.0")
        BigDecimal outstandingBalance,

        @NotNull
        LocalDate originationDate,

        @Valid
        LoanRequest loan
) {
}
