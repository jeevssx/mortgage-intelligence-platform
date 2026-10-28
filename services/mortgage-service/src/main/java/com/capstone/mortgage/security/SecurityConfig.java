package com.capstone.mortgage.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * Stateless JWT resource server. CSRF is disabled because there is no browser session/cookie —
 * every request carries its own bearer token, so there is no CSRF attack surface to defend
 * (OWASP API Security: CSRF protection is a session-cookie concern). See
 * docs/security/security-controls.md.
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http,
                                            JwtService jwtService,
                                            RestAuthenticationEntryPoint authenticationEntryPoint,
                                            RestAccessDeniedHandler accessDeniedHandler) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(authorize -> authorize
                        // /actuator/health/** covers /actuator/health, /actuator/health/readiness, and
                        // /actuator/health/liveness in one matcher — the two listed as top-level
                        // /actuator/readiness and /actuator/liveness paths (wrong; Spring Boot nests
                        // probe groups under /health) were silently 401ing since M4 until this was
                        // actually tested live during the M9 incident simulation (docs/operations/rca-2026-10-28.md).
                        .requestMatchers("/actuator/health/**", "/api/v1/auth/login").permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint(authenticationEntryPoint)
                        .accessDeniedHandler(accessDeniedHandler))
                .addFilterBefore(new RateLimitFilter(), UsernamePasswordAuthenticationFilter.class)
                .addFilterBefore(new JwtAuthenticationFilter(jwtService), UsernamePasswordAuthenticationFilter.class)
                .addFilterAfter(new SecurityHeadersFilter(), UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
