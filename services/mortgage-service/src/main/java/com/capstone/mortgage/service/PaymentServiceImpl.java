package com.capstone.mortgage.service;

import com.capstone.mortgage.configuration.CorrelationIdHolder;
import com.capstone.mortgage.dto.PageResponse;
import com.capstone.mortgage.dto.PaymentRequest;
import com.capstone.mortgage.dto.PaymentResponse;
import com.capstone.mortgage.entity.IdempotencyRecord;
import com.capstone.mortgage.entity.Mortgage;
import com.capstone.mortgage.entity.Payment;
import com.capstone.mortgage.entity.ServicingHistory;
import com.capstone.mortgage.exception.ConflictException;
import com.capstone.mortgage.exception.NotFoundException;
import com.capstone.mortgage.mapper.PaymentMapper;
import com.capstone.mortgage.repository.IdempotencyRecordRepository;
import com.capstone.mortgage.repository.MortgageRepository;
import com.capstone.mortgage.repository.PaymentRepository;
import com.capstone.mortgage.repository.ServicingHistoryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.time.OffsetDateTime;

/**
 * Owns the payment-posting transaction described in M4 task 4.2: a single @Transactional method
 * writes the payment row, updates the mortgage balance, and appends a servicing_history event so
 * none of the three can be left half-applied.
 */
@Service
public class PaymentServiceImpl implements PaymentService {

    private static final Logger log = LoggerFactory.getLogger(PaymentServiceImpl.class);
    private static final String PAYMENTS_PATH_TEMPLATE = "/api/v1/mortgages/{id}/payments";

    private final MortgageRepository mortgageRepository;
    private final PaymentRepository paymentRepository;
    private final ServicingHistoryRepository servicingHistoryRepository;
    private final IdempotencyRecordRepository idempotencyRecordRepository;

    public PaymentServiceImpl(MortgageRepository mortgageRepository, PaymentRepository paymentRepository,
                               ServicingHistoryRepository servicingHistoryRepository,
                               IdempotencyRecordRepository idempotencyRecordRepository) {
        this.mortgageRepository = mortgageRepository;
        this.paymentRepository = paymentRepository;
        this.servicingHistoryRepository = servicingHistoryRepository;
        this.idempotencyRecordRepository = idempotencyRecordRepository;
    }

    @Override
    @Transactional
    public PaymentResponse postPayment(String mortgageExternalId, PaymentRequest request, String idempotencyKey) {
        if (StringUtils.hasText(idempotencyKey)
                && idempotencyRecordRepository.findByIdempotencyKeyAndRequestPath(idempotencyKey, PAYMENTS_PATH_TEMPLATE).isPresent()) {
            throw new ConflictException("DUPLICATE_REQUEST",
                    "Idempotency-Key " + idempotencyKey + " was already used for this endpoint");
        }

        Mortgage mortgage = mortgageRepository.findByMortgageExternalId(mortgageExternalId)
                .orElseThrow(() -> new NotFoundException("MORTGAGE_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " was not found"));

        Payment payment = new Payment();
        payment.setMortgage(mortgage);
        payment.setDueDate(request.dueDate());
        payment.setPaidDate(request.paidDate());
        payment.setAmount(request.amount());
        payment.setStatus(request.status());
        Payment savedPayment = paymentRepository.save(payment);

        applyBalanceEffect(mortgage, savedPayment);
        mortgageRepository.save(mortgage);

        ServicingHistory event = new ServicingHistory();
        event.setMortgage(mortgage);
        event.setEventTime(OffsetDateTime.now());
        event.setEventType("PAYMENT_" + request.status().name());
        event.setDescription("Payment " + request.amount() + " " + request.status().name().toLowerCase());
        servicingHistoryRepository.save(event);

        if (StringUtils.hasText(idempotencyKey)) {
            IdempotencyRecord record = new IdempotencyRecord();
            record.setIdempotencyKey(idempotencyKey);
            record.setRequestPath(PAYMENTS_PATH_TEMPLATE);
            record.setResponseReference(savedPayment.getId().toString());
            idempotencyRecordRepository.save(record);
        }

        log.info("Payment posted mortgageExternalId={} amount={} status={} correlationId={}",
                mortgageExternalId, request.amount(), request.status(), CorrelationIdHolder.get());

        return PaymentMapper.toResponse(savedPayment);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<PaymentResponse> listPayments(String mortgageExternalId, Pageable pageable) {
        Mortgage mortgage = mortgageRepository.findByMortgageExternalId(mortgageExternalId)
                .orElseThrow(() -> new NotFoundException("MORTGAGE_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " was not found"));
        Page<PaymentResponse> page = paymentRepository.findByMortgageOrderByDueDateDesc(mortgage, pageable)
                .map(PaymentMapper::toResponse);
        return PageResponse.from(page);
    }

    private void applyBalanceEffect(Mortgage mortgage, Payment payment) {
        BigDecimal balance = mortgage.getOutstandingBalance();
        switch (payment.getStatus()) {
            case POSTED -> mortgage.setOutstandingBalance(max(balance.subtract(payment.getAmount()), BigDecimal.ZERO));
            case REVERSED -> mortgage.setOutstandingBalance(
                    min(balance.add(payment.getAmount()), mortgage.getOriginalAmount()));
            case SCHEDULED, FAILED -> { /* no balance effect */ }
        }
    }

    private static BigDecimal max(BigDecimal a, BigDecimal b) {
        return a.compareTo(b) >= 0 ? a : b;
    }

    private static BigDecimal min(BigDecimal a, BigDecimal b) {
        return a.compareTo(b) <= 0 ? a : b;
    }
}
