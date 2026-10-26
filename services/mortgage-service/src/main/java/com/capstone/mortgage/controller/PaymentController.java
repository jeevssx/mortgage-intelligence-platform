package com.capstone.mortgage.controller;

import com.capstone.mortgage.dto.PageResponse;
import com.capstone.mortgage.dto.PaymentRequest;
import com.capstone.mortgage.dto.PaymentResponse;
import com.capstone.mortgage.service.PaymentService;
import jakarta.validation.Valid;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/mortgages/{mortgageExternalId}/payments")
public class PaymentController {

    private final PaymentService paymentService;

    public PaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @PostMapping
    public ResponseEntity<PaymentResponse> postPayment(
            @PathVariable String mortgageExternalId,
            @Valid @RequestBody PaymentRequest request,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {
        PaymentResponse response = paymentService.postPayment(mortgageExternalId, request, idempotencyKey);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping
    public PageResponse<PaymentResponse> listPayments(
            @PathVariable String mortgageExternalId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size);
        return paymentService.listPayments(mortgageExternalId, pageable);
    }
}
