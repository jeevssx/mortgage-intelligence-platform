package com.capstone.mortgage.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

import com.fasterxml.jackson.databind.ObjectMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Plain-object test (no Spring context) for the fail-fast behavior around the insecure dev-only
 * JWT secret default — see "Known gaps" / R-1 in docs/security/vulnerability-report.md.
 */
class JwtServiceTest {

    private static final String INSECURE_SECRET = "insecure-dev-only-shared-secret-please-override-in-prod-env";
    private static final String REAL_SECRET = "a-real-32-byte-or-longer-secret-for-this-test-xx";

    @Test
    void insecureDefault_underDevProfile_startsWithWarningOnly() {
        MockEnvironment env = new MockEnvironment().withProperty("spring.profiles.active", "dev");
        env.setActiveProfiles("dev");
        JwtService service = new JwtService(INSECURE_SECRET, "capstone-mortgage-auth", 3600, env);
        assertThat(service.generateToken("user@example.test", "ADMIN")).isNotBlank();
    }

    @Test
    void insecureDefault_underNonLocalProfile_refusesToStart() {
        MockEnvironment env = new MockEnvironment();
        env.setActiveProfiles("staging");
        assertThatThrownBy(() -> new JwtService(INSECURE_SECRET, "capstone-mortgage-auth", 3600, env))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("refusing to start");
    }

    @Test
    void realSecret_underNonLocalProfile_startsNormally() {
        MockEnvironment env = new MockEnvironment();
        env.setActiveProfiles("staging");
        JwtService service = new JwtService(REAL_SECRET, "capstone-mortgage-auth", 3600, env);
        assertThat(service.generateToken("user@example.test", "ADMIN")).isNotBlank();
    }

    /**
     * Regression test: JJWT's bare {@code signWith(key)} auto-selects the strongest algorithm
     * the key length supports (HS384/HS512 for secrets this long), not HS256. ai-assistant's
     * PyJWT decode hardcodes {@code algorithms=["HS256"]} (src/api/security.py), so a token
     * signed with anything else is silently rejected as "invalid Bearer token" — this is exactly
     * how the ai-assistant /ask endpoint ended up rejecting every real end-to-end token until
     * this was found via the M10 E2E suite. servicing-service's validator doesn't pin an
     * algorithm so it never caught this; this test pins the issuing side instead.
     */
    @Test
    void generateToken_alwaysSignsWithHs256_regardlessOfSecretLength() throws Exception {
        MockEnvironment env = new MockEnvironment().withProperty("spring.profiles.active", "dev");
        env.setActiveProfiles("dev");
        // Long enough that JJWT's auto-selection would otherwise pick HS384/HS512.
        String longSecret = "compose-dev-only-shared-jwt-secret-never-use-outside-this-stack";
        JwtService service = new JwtService(longSecret, "capstone-mortgage-auth", 3600, env);

        String token = service.generateToken("user@example.test", "ADMIN");
        String headerJson = new String(
                Base64.getUrlDecoder().decode(token.split("\\.")[0]), StandardCharsets.UTF_8);
        String alg = new ObjectMapper().readTree(headerJson).get("alg").asText();

        assertThat(alg).isEqualTo("HS256");
    }
}
