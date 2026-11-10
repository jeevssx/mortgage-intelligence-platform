package com.capstone.mortgage.dto;

import com.capstone.mortgage.entity.UnderwritingDecision;
import jakarta.validation.constraints.*;

import java.math.BigDecimal;

public record LoanRequest(

        @NotBlank @Pattern(regexp = "^LOAN-[0-9]{4}$", message = "must match LOAN-####")
        String loanExternalId,

        @NotNull @DecimalMin(value = "0.0", inclusive = false) @DecimalMax(value = "1.0", inclusive = false)
        BigDecimal interestRate,

        @NotNull @Min(1) @Max(480)
        Integer termMonths,

        UnderwritingDecision underwritingDecision
) {
}
