package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.MortgageRequest;
import com.capstone.mortgage.dto.MortgageResponse;
import com.capstone.mortgage.dto.PageResponse;
import org.springframework.data.domain.Pageable;

public interface MortgageService {
    MortgageResponse create(MortgageRequest request);
    MortgageResponse getByExternalId(String mortgageExternalId);
    PageResponse<MortgageResponse> list(String borrowerExternalId, Pageable pageable);
}
