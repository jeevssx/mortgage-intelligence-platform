package com.capstone.mortgage.dto;

import java.time.LocalDate;
import java.util.UUID;

public record BorrowerResponse(
        UUID id,
        String borrowerExternalId,
        String firstName,
        String lastName,
        String email,
        String phone,
        LocalDate dateOfBirth
) {
}
