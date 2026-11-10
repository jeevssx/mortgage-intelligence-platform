package com.capstone.mortgage.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Reads "Authorization: Bearer <jwt>", validates it, and populates the SecurityContext with the
 * username as principal and roles as authorities (no ROLE_ prefix — @PreAuthorize expressions
 * use hasAnyAuthority with the raw role codes from guides/standards.md). An invalid/expired/
 * missing token simply leaves the context unauthenticated; the filter chain's
 * authorizeHttpRequests rules decide whether that's a 401.
 *
 * Deliberately NOT a @Component: it's wired into Spring Security's chain via
 * SecurityConfig#filterChain. A Filter bean picked up by Spring Boot's generic auto-registration
 * would run a second time as an independent servlet filter outside that chain.
 */
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

    private final JwtService jwtService;

    public JwtAuthenticationFilter(JwtService jwtService) {
        this.jwtService = jwtService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (StringUtils.hasText(header) && header.startsWith("Bearer ")) {
            String token = header.substring("Bearer ".length());
            try {
                Claims claims = jwtService.parseAndValidate(token);
                List<GrantedAuthority> authorities = jwtService.rolesOf(claims).stream()
                        .map(SimpleGrantedAuthority::new)
                        .map(GrantedAuthority.class::cast)
                        .toList();
                var authentication = new UsernamePasswordAuthenticationToken(claims.getSubject(), null, authorities);
                SecurityContextHolder.getContext().setAuthentication(authentication);
            } catch (JwtException ex) {
                log.debug("JWT_REJECTED reason={}", ex.getMessage());
            }
        }
        chain.doFilter(request, response);
    }
}
