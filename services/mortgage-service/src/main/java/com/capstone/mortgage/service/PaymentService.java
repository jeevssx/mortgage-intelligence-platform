package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.PageResponse;
import com.capstone.mortgage.dto.PaymentRequest;
import com.capstone.mortgage.dto.PaymentResponse;
import org.springframework.data.domain.Pageable;

public interface PaymentService {
    PaymentResponse postPayment(String mortgageExternalId, PaymentRequest request, String idempotencyKey);
    PageResponse<PaymentResponse> listPayments(String mortgageExternalId, Pageable pageable);
}
