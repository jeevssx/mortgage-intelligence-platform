package com.capstone.mortgage.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import java.time.LocalDate;

public record BorrowerRequest(

        @NotBlank @Pattern(regexp = "^BOR-[0-9]{3}$", message = "must match BOR-###")
        String borrowerExternalId,

        @NotBlank String firstName,

        @NotBlank String lastName,

        @NotBlank @Email String email,

        String phone,

        LocalDate dateOfBirth
) {
}
