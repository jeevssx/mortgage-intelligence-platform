package com.capstone.servicing.controller;

import com.capstone.servicing.entity.Mortgage;
import com.capstone.servicing.entity.MortgageStatus;
import com.capstone.servicing.repository.MortgageRepository;
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
class RbacTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private MortgageRepository mortgageRepository;

    private static final String EVENT_PAYLOAD = """
            {"eventType": "DOCUMENT_UPLOADED", "description": "test"}
            """;

    @BeforeEach
    void seedMortgage() {
        Mortgage mortgage = new Mortgage();
        mortgage.setMortgageExternalId("MTG-1001");
        mortgage.setStatus(MortgageStatus.ACTIVE);
        mortgageRepository.save(mortgage);
    }

    @Test
    void recordEvent_withoutToken_returns401() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events").contentType("application/json").content(EVENT_PAYLOAD))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    @Test
    void actuatorHealthProbeGroups_arePublic_withoutAToken() throws Exception {
        // Regression test for docs/operations/rca-2026-10-28.md — must run in a test class with
        // no class-level @WithMockUser, since that would mask a permitAll misconfiguration by
        // satisfying the authenticated() fallback regardless.
        mockMvc.perform(get("/actuator/health/readiness")).andExpect(status().isOk());
        mockMvc.perform(get("/actuator/health/liveness")).andExpect(status().isOk());
    }

    @Test
    @WithMockUser(authorities = "UNDERWRITER")
    void recordEvent_underwriter_returns403() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events").contentType("application/json").content(EVENT_PAYLOAD))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("FORBIDDEN"));
    }

    @Test
    @WithMockUser(authorities = "RISK_ANALYST")
    void recordEvent_riskAnalyst_returns403() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events").contentType("application/json").content(EVENT_PAYLOAD))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(authorities = "SERVICING_AGENT")
    void recordEvent_servicingAgent_returns201() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events").contentType("application/json").content(EVENT_PAYLOAD))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(authorities = "ADMIN")
    void recordEvent_admin_returns201() throws Exception {
        mockMvc.perform(post("/api/v1/mortgages/MTG-1001/servicing-events").contentType("application/json").content(EVENT_PAYLOAD))
                .andExpect(status().isCreated());
    }

    @Test
    @WithMockUser(authorities = "SUPPORT")
    void getServicingHistory_anyAuthenticatedRole_returns200() throws Exception {
        mockMvc.perform(get("/api/v1/mortgages/MTG-1001/servicing-history"))
                .andExpect(status().isOk());
    }
}
