package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.LoginRequest;
import com.capstone.mortgage.dto.LoginResponse;

public interface AuthService {
    LoginResponse login(LoginRequest request);
}
