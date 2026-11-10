package com.capstone.servicing.controller;

import com.capstone.servicing.entity.*;
import com.capstone.servicing.repository.DelinquencyRepository;
import com.capstone.servicing.repository.MortgageRepository;
import com.capstone.servicing.repository.ServicingHistoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.OffsetDateTime;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
@WithMockUser(authorities = "ADMIN")
class ServicingControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private MortgageRepository mortgageRepository;
    @Autowired private ServicingHistoryRepository servicingHistoryRepository;
    @Autowired private DelinquencyRepository delinquencyRepository;

    private Mortgage active;
    private Mortgage delinquent;

    @BeforeEach
    void seed() {
        active = new Mortgage();
        active.setMortgageExternalId("MTG-1001");
        active.setStatus(MortgageStatus.ACTIVE);
        active = mortgageRepository.save(active);

        ServicingHistory onboarding = new ServicingHistory();
        onboarding.setMortgage(active);
        onboarding.setEventTime(OffsetDateTime.parse("2025-06-15T10:00:00Z"));
        onboarding.setEventType("ONBOARDING_COMPLETE");
        onboarding.setDescription("Mortgage onboarded to servicing");
        servicingHistoryRepository.save(onboarding);

        ServicingHistory payment = new ServicingHistory();
        payment.setMortgage(active);
        payment.setEventTime(OffsetDateTime.parse("2026-02-01T09:30:00Z"));
        payment.setEventType("PAYMENT_POSTED");
        payment.setDescription("Payment 1850.00 posted");
        servicingHistoryRepository.save(payment);

        delinquent = new Mortgage();
        delinquent.setMortgageExternalId("MTG-1002");
        delinquent.setStatus(MortgageStatus.DELINQUENT);
        delinquent = mortgageRepository.save(delinquent);

        Delinquency d = new Delinquency();
        d.setMortgage(delinquent);
        d.setDelinquentSince(LocalDate.of(2026, 1, 10));
        d.setDaysPastDue(45);
        d.setSeverity(DelinquencySeverity.MODERATE);
        delinquencyRepository.save(d);
    }

    @Test
    void getServicingHistory_returnsEventsOrderedByTime() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-1001/servicing-history"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.events[0].eventType").value("ONBOARDING_COMPLETE"))
                .andExpect(jsonPath("$.events[1].eventType").value("PAYMENT_POSTED"));
    }

    @Test
    void getDelinquency_returnsDaysPastDueAtLeast30() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-1002/delinquency"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("DELINQUENT"))
                .andExpect(jsonPath("$.daysPastDue").value(45))
                .andExpect(jsonPath("$.severity").value("MODERATE"));
    }

    @Test
    void getServicingHistory_unknownMortgage_returns404() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-9999/servicing-history"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("MORTGAGE_NOT_FOUND"));
    }

    @Test
    void getDelinquency_activeMortgageWithoutRecord_returns404() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-1001/delinquency"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("DELINQUENCY_NOT_FOUND"));
    }

    @Test
    void recordEvent_internalEndpoint_createsHistoryRow() throws Exception {
        long before = servicingHistoryRepository.findByMortgageOrderByEventTimeAsc(active).size();
        String payload = """
                {"eventType": "DOCUMENT_UPLOADED", "description": "Income verification received"}
                """;
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events")
                        .contentType("application/json")
                        .content(payload))
                .andExpect(status().isCreated());

        org.assertj.core.api.Assertions.assertThat(
                servicingHistoryRepository.findByMortgageOrderByEventTimeAsc(active).size()).isEqualTo((int) before + 1);
    }

    @Test
    void getFastLookup_withoutDynamoDbConfigured_returns404() throws Exception {
        // DYNAMODB_TABLE_MORTGAGE_LOOKUP is unset in the test profile — see
        // MortgageLookupRepository and docs/architecture/aws-iam-matrix.md (M8 task 8.4).
        mockMvc.perform(get("/api/v1/mortgages/MTG-1001/fast-lookup"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("LOOKUP_NOT_CONFIGURED"));
    }
}
