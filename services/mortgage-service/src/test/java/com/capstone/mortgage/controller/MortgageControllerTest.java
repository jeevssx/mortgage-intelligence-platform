package com.capstone.mortgage.controller;

import com.capstone.mortgage.entity.Borrower;
import com.capstone.mortgage.repository.BorrowerRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
@WithMockUser(authorities = "ADMIN")
class MortgageControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private BorrowerRepository borrowerRepository;

    @BeforeEach
    void seedBorrower() {
        Borrower borrower = new Borrower();
        borrower.setBorrowerExternalId("BOR-001");
        borrower.setFirstName("Pat");
        borrower.setLastName("Nguyen");
        borrower.setEmail("pat.nguyen@example.test");
        borrowerRepository.save(borrower);
    }

    @Test
    void createAndGetMortgage_happyPath() throws Exception {
        String payload = """
                {
                  "mortgageExternalId": "MTG-1010",
                  "borrowerExternalId": "BOR-001",
                  "originalAmount": 320000.00,
                  "outstandingBalance": 318500.00,
                  "originationDate": "2025-06-01",
                  "loan": {
                    "loanExternalId": "LOAN-2010",
                    "interestRate": 0.0650,
                    "termMonths": 360,
                    "underwritingDecision": "APPROVED"
                  }
                }
                """;

        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(payload))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.mortgageExternalId").value("MTG-1010"))
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andExpect(jsonPath("$.loan.loanExternalId").value("LOAN-2010"));

        mockMvc.perform(get("/api/v1/mortgages/MTG-1010"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.borrowerExternalId").value("BOR-001"));
    }

    @Test
    void listMortgages_filtersByBorrower() throws Exception {
        String payload = """
                {"mortgageExternalId": "MTG-1020", "borrowerExternalId": "BOR-001",
                 "originalAmount": 200000.00, "outstandingBalance": 200000.00,
                 "originationDate": "2026-01-01"}
                """;
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(payload))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/api/v1/mortgages").param("borrowerId", "BOR-001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[0].borrowerExternalId").value("BOR-001"))
                .andExpect(jsonPath("$.totalElements").value(1));
    }

    @Test
    void createMortgage_unknownBorrower_returns404() throws Exception {
        String payload = """
                {"mortgageExternalId": "MTG-1030", "borrowerExternalId": "BOR-999",
                 "originalAmount": 100000.00, "outstandingBalance": 100000.00,
                 "originationDate": "2026-01-01"}
                """;
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(payload))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("BORROWER_NOT_FOUND"));
    }

    @Test
    void getMortgage_unknown_returns404() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-9999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("MORTGAGE_NOT_FOUND"));
    }

    @Test
    void createMortgage_negativeBalance_returns400() throws Exception {
        String payload = """
                {"mortgageExternalId": "MTG-1040", "borrowerExternalId": "BOR-001",
                 "originalAmount": 100000.00, "outstandingBalance": -5.00,
                 "originationDate": "2026-01-01"}
                """;
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(payload))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"));
    }
}
