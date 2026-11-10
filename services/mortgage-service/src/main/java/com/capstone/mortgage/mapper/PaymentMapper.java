package com.capstone.mortgage.mapper;

import com.capstone.mortgage.dto.PaymentResponse;
import com.capstone.mortgage.entity.Payment;

public final class PaymentMapper {

    private PaymentMapper() { }

    public static PaymentResponse toResponse(Payment payment) {
        return new PaymentResponse(
                payment.getId(),
                payment.getMortgage().getMortgageExternalId(),
                payment.getDueDate(),
                payment.getPaidDate(),
                payment.getAmount(),
                payment.getStatus(),
                payment.getMortgage().getOutstandingBalance()
        );
    }
}
