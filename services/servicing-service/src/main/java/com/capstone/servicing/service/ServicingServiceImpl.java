package com.capstone.servicing.service;

import com.capstone.servicing.dto.DelinquencyResponse;
import com.capstone.servicing.dto.ServicingEventRequest;
import com.capstone.servicing.dto.ServicingHistoryEvent;
import com.capstone.servicing.dto.ServicingHistoryResponse;
import com.capstone.servicing.configuration.CorrelationIdHolder;
import com.capstone.servicing.entity.Delinquency;
import com.capstone.servicing.entity.Mortgage;
import com.capstone.servicing.entity.ServicingHistory;
import com.capstone.servicing.exception.NotFoundException;
import com.capstone.servicing.dto.MortgageLookupResponse;
import com.capstone.servicing.lookup.MortgageLookupRepository;
import com.capstone.servicing.messaging.EventEnvelope;
import com.capstone.servicing.messaging.EventPublisher;
import com.capstone.servicing.repository.DelinquencyRepository;
import com.capstone.servicing.repository.MortgageRepository;
import com.capstone.servicing.repository.ServicingHistoryRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

@Service
public class ServicingServiceImpl implements ServicingService {

    private static final String LOAN_DELINQUENT_EVENT_TYPE = "LOAN_DELINQUENT";

    private final MortgageRepository mortgageRepository;
    private final ServicingHistoryRepository servicingHistoryRepository;
    private final DelinquencyRepository delinquencyRepository;
    private final EventPublisher eventPublisher;
    private final MortgageLookupRepository lookupRepository;

    public ServicingServiceImpl(MortgageRepository mortgageRepository,
                                 ServicingHistoryRepository servicingHistoryRepository,
                                 DelinquencyRepository delinquencyRepository,
                                 EventPublisher eventPublisher,
                                 MortgageLookupRepository lookupRepository) {
        this.mortgageRepository = mortgageRepository;
        this.servicingHistoryRepository = servicingHistoryRepository;
        this.delinquencyRepository = delinquencyRepository;
        this.eventPublisher = eventPublisher;
        this.lookupRepository = lookupRepository;
    }

    @Override
    @Transactional(readOnly = true)
    public ServicingHistoryResponse getServicingHistory(String mortgageExternalId) {
        Mortgage mortgage = findMortgageOrThrow(mortgageExternalId);
        List<ServicingHistoryEvent> events = servicingHistoryRepository.findByMortgageOrderByEventTimeAsc(mortgage)
                .stream()
                .map(e -> new ServicingHistoryEvent(e.getEventTime(), e.getEventType(), e.getDescription()))
                .toList();
        return new ServicingHistoryResponse(mortgageExternalId, events);
    }

    @Override
    @Transactional(readOnly = true)
    public DelinquencyResponse getDelinquency(String mortgageExternalId) {
        Mortgage mortgage = findMortgageOrThrow(mortgageExternalId);
        Delinquency delinquency = delinquencyRepository.findByMortgage(mortgage)
                .orElseThrow(() -> new NotFoundException("DELINQUENCY_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " has no delinquency record"));
        return new DelinquencyResponse(
                mortgageExternalId,
                mortgage.getStatus().name(),
                delinquency.getDelinquentSince(),
                delinquency.getDaysPastDue(),
                delinquency.getSeverity().name());
    }

    @Override
    @Transactional
    public void recordEvent(String mortgageExternalId, ServicingEventRequest request) {
        Mortgage mortgage = findMortgageOrThrow(mortgageExternalId);
        ServicingHistory event = new ServicingHistory();
        event.setMortgage(mortgage);
        event.setEventTime(OffsetDateTime.now());
        event.setEventType(request.eventType());
        event.setDescription(request.description());
        servicingHistoryRepository.save(event);

        if (LOAN_DELINQUENT_EVENT_TYPE.equals(request.eventType())) {
            delinquencyRepository.findByMortgage(mortgage).ifPresentOrElse(
                    delinquency -> eventPublisher.publish(EventEnvelope.of("LoanDelinquent", CorrelationIdHolder.get(), Map.of(
                            "mortgageExternalId", mortgageExternalId,
                            "daysPastDue", delinquency.getDaysPastDue(),
                            "severity", delinquency.getSeverity().name()))),
                    () -> { /* no delinquency row yet; nothing to publish */ });
        }
    }

    @Override
    public MortgageLookupResponse getFastLookup(String mortgageExternalId) {
        if (!lookupRepository.isEnabled()) {
            throw new NotFoundException("LOOKUP_NOT_CONFIGURED",
                    "DynamoDB fast lookup is not configured (DYNAMODB_TABLE_MORTGAGE_LOOKUP unset)");
        }
        return lookupRepository.find(mortgageExternalId)
                .map(r -> new MortgageLookupResponse(r.mortgageExternalId(), r.borrowerExternalId(),
                        r.status(), r.outstandingBalance(), "DynamoDB"))
                .orElseThrow(() -> new NotFoundException("MORTGAGE_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " was not found in the fast lookup table"));
    }

    private Mortgage findMortgageOrThrow(String mortgageExternalId) {
        return mortgageRepository.findByMortgageExternalId(mortgageExternalId)
                .orElseThrow(() -> new NotFoundException("MORTGAGE_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " was not found"));
    }
}
