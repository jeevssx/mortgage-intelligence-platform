package com.capstone.mortgage.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.util.Set;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.List;

/**
 * Issues and validates HS256 JWTs. The signing key (JWT_SECRET) must be identical in
 * servicing-service so it can validate tokens this service issues without an inter-service call
 * — see guides/standards.md and docs/security/security-controls.md.
 */
@Component
public class JwtService {

    private static final Logger log = LoggerFactory.getLogger(JwtService.class);
    private static final String ROLES_CLAIM = "roles";
    private static final String INSECURE_DEFAULT_PREFIX = "insecure-dev-only";
    private static final Set<String> LOCAL_PROFILES = Set.of("dev", "test", "default");

    private final SecretKey key;
    private final String issuer;
    private final long expirySeconds;

    public JwtService(
            @Value("${capstone.security.jwt-secret}") String secret,
            @Value("${capstone.security.jwt-issuer}") String issuer,
            @Value("${capstone.security.jwt-expiry-seconds}") long expirySeconds,
            Environment env) {
        if (secret.startsWith(INSECURE_DEFAULT_PREFIX)) {
            boolean localProfile = env.getActiveProfiles().length == 0
                    || Set.of(env.getActiveProfiles()).stream().anyMatch(LOCAL_PROFILES::contains);
            if (!localProfile) {
                // Fail fast rather than silently running with a secret anyone can read in this
                // public repo — see "Remediated" R-1 in docs/security/vulnerability-report.md.
                throw new IllegalStateException(
                        "JWT_SECRET must be set outside dev/test profiles (active: " +
                        String.join(",", env.getActiveProfiles()) + ") — refusing to start with the insecure default.");
            }
            log.warn("JWT_SECRET is not set — using the insecure dev-only default. " +
                    "Never use this outside local development (docs/security/security-controls.md).");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.issuer = issuer;
        this.expirySeconds = expirySeconds;
    }

    public String generateToken(String username, String role) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(username)
                .issuer(issuer)
                .claim(ROLES_CLAIM, List.of(role))
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(expirySeconds)))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    public long expirySeconds() {
        return expirySeconds;
    }

    /** @throws JwtException if the token is malformed, expired, or has an invalid signature. */
    public Claims parseAndValidate(String token) {
        return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
    }

    @SuppressWarnings("unchecked")
    public List<String> rolesOf(Claims claims) {
        return (List<String>) claims.get(ROLES_CLAIM, List.class);
    }
}
