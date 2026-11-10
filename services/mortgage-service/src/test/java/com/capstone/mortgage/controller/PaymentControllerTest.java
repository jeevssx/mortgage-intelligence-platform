package com.capstone.mortgage.controller;

import com.capstone.mortgage.entity.Borrower;
import com.capstone.mortgage.entity.Mortgage;
import com.capstone.mortgage.entity.MortgageStatus;
import com.capstone.mortgage.repository.BorrowerRepository;
import com.capstone.mortgage.repository.MortgageRepository;
import com.capstone.mortgage.repository.ServicingHistoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
@WithMockUser(authorities = "ADMIN")
class PaymentControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private BorrowerRepository borrowerRepository;
    @Autowired private MortgageRepository mortgageRepository;
    @Autowired private ServicingHistoryRepository servicingHistoryRepository;

    private Mortgage mortgage;

    @BeforeEach
    void seedMortgage() {
        Borrower borrower = new Borrower();
        borrower.setBorrowerExternalId("BOR-001");
        borrower.setFirstName("Pat");
        borrower.setLastName("Nguyen");
        borrower.setEmail("pat.nguyen@example.test");
        borrowerRepository.save(borrower);

        mortgage = new Mortgage();
        mortgage.setMortgageExternalId("MTG-1001");
        mortgage.setBorrower(borrower);
        mortgage.setStatus(MortgageStatus.ACTIVE);
        mortgage.setOriginalAmount(new BigDecimal("320000.00"));
        mortgage.setOutstandingBalance(new BigDecimal("318500.00"));
        mortgage.setOriginationDate(LocalDate.of(2025, 6, 1));
        mortgage = mortgageRepository.save(mortgage);
    }

    @Test
    void postPayment_posted_decrementsBalanceAndRecordsServicingEvent() throws Exception {
        long eventsBefore = servicingHistoryRepository.countByMortgage(mortgage);
        String payload = """
                {"dueDate": "2026-03-01", "paidDate": "2026-03-02", "amount": 1850.00, "status": "POSTED"}
                """;

        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments")
                        .contentType("application/json")
                        .header("X-Correlation-Id", "m4-pay-001")
                        .header("Idempotency-Key", "pay-MTG-1001-2026-03-01")
                        .content(payload))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.outstandingBalanceAfter").value(316650.00));

        assertThat(servicingHistoryRepository.countByMortgage(mortgage)).isEqualTo(eventsBefore + 1);
    }

    @Test
    void postPayment_duplicateIdempotencyKey_returns409() throws Exception {
        String payload = """
                {"dueDate": "2026-03-01", "paidDate": "2026-03-02", "amount": 1850.00, "status": "POSTED"}
                """;

        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments")
                        .contentType("application/json")
                        .header("Idempotency-Key", "pay-dup-001")
                        .content(payload))
                .andExpect(status().isCreated());

        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments")
                        .contentType("application/json")
                        .header("Idempotency-Key", "pay-dup-001")
                        .content(payload))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("DUPLICATE_REQUEST"));
    }

    @Test
    void postPayment_invalidAmount_returns400WithErrorEnvelope() throws Exception {
        String payload = """
                {"dueDate": "2026-03-01", "amount": -10.00, "status": "POSTED"}
                """;

        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments")
                        .contentType("application/json")
                        .header("X-Correlation-Id", "m4-pay-invalid")
                        .content(payload))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.correlationId").value("m4-pay-invalid"));
    }

    @Test
    void postPayment_unknownMortgage_returns404() throws Exception {
        String payload = """
                {"dueDate": "2026-03-01", "amount": 100.00, "status": "POSTED"}
                """;
        mockMvc.perform(post("/api/v1/mortgages/MTG-9999/payments")
                        .contentType("application/json")
                        .content(payload))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("MORTGAGE_NOT_FOUND"));
    }

    @Test
    void listPayments_returnsPagedResults() throws Exception {
        String payload = """
                {"dueDate": "2026-03-01", "paidDate": "2026-03-02", "amount": 1850.00, "status": "POSTED"}
                """;
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/payments").contentType("application/json").content(payload))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/api/v1/mortgages/MTG-1001/payments"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalElements").value(1));
    }
}
