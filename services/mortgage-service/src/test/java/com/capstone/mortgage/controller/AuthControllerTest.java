package com.capstone.mortgage.controller;

import com.capstone.mortgage.entity.AppUser;
import com.capstone.mortgage.repository.AppUserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Exercises the real login -> JWT -> protected-endpoint path end-to-end (no @WithMockUser),
 * proving JwtService/JwtAuthenticationFilter actually work, not just the authorization rules.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
class AuthControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private AppUserRepository appUserRepository;
    @Autowired private PasswordEncoder passwordEncoder;

    @BeforeEach
    void seedUser() {
        AppUser user = new AppUser();
        user.setUsername("servicing@capstone.local");
        user.setPasswordHash(passwordEncoder.encode("TestPass123!"));
        user.setRole("SERVICING_AGENT");
        appUserRepository.save(user);
    }

    @Test
    void login_validCredentials_returnsJwtUsableOnProtectedEndpoint() throws Exception {
        String loginPayload = """
                {"username": "servicing@capstone.local", "password": "TestPass123!"}
                """;

        String body = mockMvc.perform(post("/api/v1/auth/login").contentType("application/json").content(loginPayload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.roles[0]").value("SERVICING_AGENT"))
                .andExpect(jsonPath("$.accessToken").exists())
                .andReturn().getResponse().getContentAsString();

        String token = body.replaceAll(".*\"accessToken\"\\s*:\\s*\"([^\"]+)\".*", "$1");

        // GET /api/v1/borrowers/{id} only requires an authenticated user, not a specific role.
        mockMvc.perform(get("/api/v1/borrowers/BOR-999").header("Authorization", "Bearer " + token))
                .andExpect(status().isNotFound()); // 404, not 401 — proves the token was accepted
    }

    @Test
    void login_wrongPassword_returns401() throws Exception {
        String payload = """
                {"username": "servicing@capstone.local", "password": "wrong-password"}
                """;
        mockMvc.perform(post("/api/v1/auth/login").contentType("application/json").content(payload))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
    }

    @Test
    void login_unknownUsername_returns401() throws Exception {
        String payload = """
                {"username": "nobody@capstone.local", "password": "whatever"}
                """;
        mockMvc.perform(post("/api/v1/auth/login").contentType("application/json").content(payload))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void protectedEndpoint_withoutToken_returns401() throws Exception {
        mockMvc.perform(get("/api/v1/borrowers/BOR-001"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }

    @Test
    void protectedEndpoint_withTamperedToken_returns401() throws Exception {
        mockMvc.perform(get("/api/v1/borrowers/BOR-001").header("Authorization", "Bearer not-a-real-jwt"))
                .andExpect(status().isUnauthorized());
    }
}
