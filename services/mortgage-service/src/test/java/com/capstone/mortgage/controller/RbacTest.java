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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * RBAC matrix from docs/security/security-controls.md, exercised for every role against the two
 * write endpoints that are role-restricted (POST /mortgages: ADMIN/UNDERWRITER only;
 * POST .../payments: ADMIN/SERVICING_AGENT only).
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class RbacTest {

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

    private static String mortgagePayload(String mortgageExternalId) {
        return """
                {"mortgageExternalId": "%s", "borrowerExternalId": "BOR-001",
                 "originalAmount": 100000.00, "outstandingBalance": 100000.00, "originationDate": "2026-01-01"}
                """.formatted(mortgageExternalId);
    }

    @Test
    @WithMockUser(authorities = "SUPPORT")
    void support_cannotCreateMortgage() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(mortgagePayload("MTG-2001")))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("FORBIDDEN"));
    }

    @Test
    @WithMockUser(authorities = "RISK_ANALYST")
    void riskAnalyst_cannotCreateMortgage() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(mortgagePayload("MTG-2002")))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(authorities = "SERVICING_AGENT")
    void servicingAgent_cannotCreateMortgage() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(mortgagePayload("MTG-2003")))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(authorities = "UNDERWRITER")
    void underwriter_canCreateMortgage() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(mortgagePayload("MTG-2004")))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(authorities = "ADMIN")
    void admin_canCreateMortgage() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages").contentType("application/json").content(mortgagePayload("MTG-2005")))
                .andExpect(status().isCreated());
    }

    private static final String PAYMENT_PAYLOAD = """
            {"dueDate": "2026-03-01", "amount": 100.00, "status": "POSTED", "paidDate": "2026-03-02"}
            """;

    @Test
    @WithMockUser(authorities = "UNDERWRITER")
    void underwriter_cannotPostPayment() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments").contentType("application/json").content(PAYMENT_PAYLOAD))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(authorities = "SUPPORT")
    void support_cannotPostPayment() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments").contentType("application/json").content(PAYMENT_PAYLOAD))
                .andExpect(status().isForbidden());
    }
}
