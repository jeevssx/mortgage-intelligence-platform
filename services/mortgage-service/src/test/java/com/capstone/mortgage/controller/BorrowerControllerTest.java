package com.capstone.mortgage.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class BorrowerControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void createAndGetBorrower_happyPath() throws Exception {
        String payload = """
                {
                  "borrowerExternalId": "BOR-010",
                  "firstName": "Alex",
                  "lastName": "Rivera",
                  "email": "alex.rivera@example.test",
                  "phone": "+1-555-0100",
                  "dateOfBirth": "1988-04-12"
                }
                """;

        mockMvc.perform(post("/api/v1/borrowers")
                        .contentType("application/json")
                        .content(payload))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.borrowerExternalId").value("BOR-010"))
                .andExpect(jsonPath("$.email").value("alex.rivera@example.test"));

        mockMvc.perform(get("/api/v1/borrowers/BOR-010"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.firstName").value("Alex"));
    }

    @Test
    void createBorrower_invalidEmail_returns400WithErrorEnvelope() throws Exception {
        String payload = """
                {
                  "borrowerExternalId": "BOR-011",
                  "firstName": "Jamie",
                  "lastName": "Lee",
                  "email": "not-an-email"
                }
                """;

        mockMvc.perform(post("/api/v1/borrowers")
                        .contentType("application/json")
                        .header("X-Correlation-Id", "test-borrower-001")
                        .content(payload))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.correlationId").value("test-borrower-001"))
                .andExpect(jsonPath("$.timestamp").exists());
    }

    @Test
    void getBorrower_unknown_returns404() throws Exception {
        mockMvc.perform(get("/api/v1/borrowers/BOR-999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("BORROWER_NOT_FOUND"));
    }

    @Test
    void createBorrower_duplicateExternalId_returns409() throws Exception {
        String payload = """
                {
                  "borrowerExternalId": "BOR-012",
                  "firstName": "Sam",
                  "lastName": "Chen",
                  "email": "sam.chen@example.test"
                }
                """;
        mockMvc.perform(post("/api/v1/borrowers").contentType("application/json").content(payload))
                .andExpect(status().isCreated());
        mockMvc.perform(post("/api/v1/borrowers").contentType("application/json").content(payload))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("BORROWER_ALREADY_EXISTS"));
    }
}
