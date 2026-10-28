package com.capstone.mortgage.dto;

import java.util.List;

public record LoginResponse(String accessToken, long expiresInSeconds, List<String> roles) {
}
