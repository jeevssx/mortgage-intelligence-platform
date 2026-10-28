package com.capstone.servicing.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThatCode;

/** See mortgage-service's JwtServiceTest for the rationale (R-1 in docs/security/vulnerability-report.md). */
class JwtValidationServiceTest {

    private static final String INSECURE_SECRET = "insecure-dev-only-shared-secret-please-override-in-prod-env";
    private static final String REAL_SECRET = "a-real-32-byte-or-longer-secret-for-this-test-xx";

    @Test
    void insecureDefault_underDevProfile_startsWithWarningOnly() {
        MockEnvironment env = new MockEnvironment();
        env.setActiveProfiles("dev");
        assertThatCode(() -> new JwtValidationService(INSECURE_SECRET, env)).doesNotThrowAnyException();
    }

    @Test
    void insecureDefault_underNonLocalProfile_refusesToStart() {
        MockEnvironment env = new MockEnvironment();
        env.setActiveProfiles("staging");
        assertThatThrownBy(() -> new JwtValidationService(INSECURE_SECRET, env))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("refusing to start");
    }

    @Test
    void realSecret_underNonLocalProfile_startsNormally() {
        MockEnvironment env = new MockEnvironment();
        env.setActiveProfiles("staging");
        assertThatCode(() -> new JwtValidationService(REAL_SECRET, env)).doesNotThrowAnyException();
    }
}
