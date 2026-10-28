package com.capstone.servicing.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;

/**
 * Validates JWTs issued by mortgage-service. JWT_SECRET must be identical across both services
 * (shared-secret HS256, no inter-service call to verify a token) — see
 * docs/security/security-controls.md and ADR-002.
 */
@Component
public class JwtValidationService {

    private static final Logger log = LoggerFactory.getLogger(JwtValidationService.class);
    private static final String ROLES_CLAIM = "roles";
    private static final String INSECURE_DEFAULT_PREFIX = "insecure-dev-only";
    private static final Set<String> LOCAL_PROFILES = Set.of("dev", "test", "default");

    private final SecretKey key;

    public JwtValidationService(@Value("${capstone.security.jwt-secret}") String secret, Environment env) {
        if (secret.startsWith(INSECURE_DEFAULT_PREFIX)) {
            boolean localProfile = env.getActiveProfiles().length == 0
                    || Set.of(env.getActiveProfiles()).stream().anyMatch(LOCAL_PROFILES::contains);
            if (!localProfile) {
                throw new IllegalStateException(
                        "JWT_SECRET must be set outside dev/test profiles (active: " +
                        String.join(",", env.getActiveProfiles()) + ") — refusing to start with the insecure default.");
            }
            log.warn("JWT_SECRET is not set — using the insecure dev-only default. " +
                    "Never use this outside local development (docs/security/security-controls.md).");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    /** @throws io.jsonwebtoken.JwtException if the token is malformed, expired, or has an invalid signature. */
    public Claims parseAndValidate(String token) {
        return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
    }

    @SuppressWarnings("unchecked")
    public List<String> rolesOf(Claims claims) {
        return (List<String>) claims.get(ROLES_CLAIM, List.class);
    }
}
