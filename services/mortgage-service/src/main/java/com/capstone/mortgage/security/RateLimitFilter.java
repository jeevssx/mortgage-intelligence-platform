package com.capstone.mortgage.security;

import com.capstone.mortgage.configuration.CorrelationIdHolder;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.OffsetDateTime;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

/**
 * Fixed-window-ish rate limit (sliding log) for the login endpoint: 10 requests per 60s per
 * client IP. In-memory and single-instance only — fine for this capstone's local/single-replica
 * deployment; a real multi-instance deployment needs a shared store (Redis) instead
 * (docs/security/security-controls.md).
 *
 * Not a @Component — see JwtAuthenticationFilter for why it's wired via SecurityConfig instead.
 */
public class RateLimitFilter extends OncePerRequestFilter {

    private static final String LIMITED_PATH = "/api/v1/auth/login";
    private static final int MAX_REQUESTS = 10;
    private static final long WINDOW_MILLIS = 60_000;

    private final Map<String, Deque<Long>> hitsByClient = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (!LIMITED_PATH.equals(request.getRequestURI())) {
            chain.doFilter(request, response);
            return;
        }

        String clientKey = request.getRemoteAddr();
        long now = System.currentTimeMillis();
        Deque<Long> hits = hitsByClient.computeIfAbsent(clientKey, k -> new ConcurrentLinkedDeque<>());
        synchronized (hits) {
            while (!hits.isEmpty() && now - hits.peekFirst() > WINDOW_MILLIS) {
                hits.pollFirst();
            }
            if (hits.size() >= MAX_REQUESTS) {
                respondTooManyRequests(response);
                return;
            }
            hits.addLast(now);
        }
        chain.doFilter(request, response);
    }

    private void respondTooManyRequests(HttpServletResponse response) throws IOException {
        response.setStatus(429); // SC_TOO_MANY_REQUESTS — not defined on jakarta.servlet.http.HttpServletResponse
        response.setContentType("application/json");
        var body = Map.of(
                "code", "RATE_LIMITED",
                "message", "Too many login attempts; try again later",
                "correlationId", String.valueOf(CorrelationIdHolder.get()),
                "timestamp", OffsetDateTime.now().toString());
        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
