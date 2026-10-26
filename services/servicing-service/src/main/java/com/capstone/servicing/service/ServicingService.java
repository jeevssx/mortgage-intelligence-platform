package com.capstone.servicing.service;

import com.capstone.servicing.dto.DelinquencyResponse;
import com.capstone.servicing.dto.ServicingEventRequest;
import com.capstone.servicing.dto.ServicingHistoryResponse;

public interface ServicingService {
    ServicingHistoryResponse getServicingHistory(String mortgageExternalId);
    DelinquencyResponse getDelinquency(String mortgageExternalId);
    void recordEvent(String mortgageExternalId, ServicingEventRequest request);
}
