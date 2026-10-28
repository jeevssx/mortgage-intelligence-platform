package com.capstone.mortgage.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

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
}
