package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.LoginRequest;
import com.capstone.mortgage.dto.LoginResponse;
import com.capstone.mortgage.entity.AppUser;
import com.capstone.mortgage.exception.UnauthorizedException;
import com.capstone.mortgage.repository.AppUserRepository;
import com.capstone.mortgage.security.JwtService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class AuthServiceImpl implements AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthServiceImpl.class);

    private final AppUserRepository appUserRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthServiceImpl(AppUserRepository appUserRepository, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.appUserRepository = appUserRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @Override
    @Transactional(readOnly = true)
    public LoginResponse login(LoginRequest request) {
        AppUser user = appUserRepository.findByUsername(request.username())
                .filter(u -> passwordEncoder.matches(request.password(), u.getPasswordHash()))
                .orElseThrow(() -> {
                    // Never log the username/password pair itself — only that an attempt failed.
                    log.warn("LOGIN_FAILED");
                    return new UnauthorizedException("INVALID_CREDENTIALS", "Invalid username or password");
                });
        String token = jwtService.generateToken(user.getUsername(), user.getRole());
        log.info("LOGIN_SUCCESS username={} role={}", user.getUsername(), user.getRole());
        return new LoginResponse(token, jwtService.expirySeconds(), List.of(user.getRole()));
    }
}
