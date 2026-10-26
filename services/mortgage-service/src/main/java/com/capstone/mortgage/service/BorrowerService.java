package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.BorrowerRequest;
import com.capstone.mortgage.dto.BorrowerResponse;

public interface BorrowerService {
    BorrowerResponse create(BorrowerRequest request);
    BorrowerResponse getByExternalId(String borrowerExternalId);
}
