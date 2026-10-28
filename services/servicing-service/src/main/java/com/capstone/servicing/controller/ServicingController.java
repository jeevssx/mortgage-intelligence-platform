package com.capstone.servicing.controller;

import com.capstone.servicing.dto.DelinquencyResponse;
import com.capstone.servicing.dto.MortgageLookupResponse;
import com.capstone.servicing.dto.ServicingEventRequest;
import com.capstone.servicing.dto.ServicingHistoryResponse;
import com.capstone.servicing.service.ServicingService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/mortgages/{mortgageExternalId}")
public class ServicingController {

    private final ServicingService servicingService;

    public ServicingController(ServicingService servicingService) {
        this.servicingService = servicingService;
    }

    @GetMapping("/servicing-history")
    public ServicingHistoryResponse getServicingHistory(@PathVariable String mortgageExternalId) {
        return servicingService.getServicingHistory(mortgageExternalId);
    }

    @GetMapping("/delinquency")
    public DelinquencyResponse getDelinquency(@PathVariable String mortgageExternalId) {
        return servicingService.getDelinquency(mortgageExternalId);
    }

    @GetMapping("/fast-lookup")
    public MortgageLookupResponse getFastLookup(@PathVariable String mortgageExternalId) {
        return servicingService.getFastLookup(mortgageExternalId);
    }

    @PostMapping("/servicing-events")
    @PreAuthorize("hasAnyAuthority('ADMIN', 'SERVICING_AGENT')")
    public ResponseEntity<Void> recordEvent(@PathVariable String mortgageExternalId,
                                             @Valid @RequestBody ServicingEventRequest request) {
        servicingService.recordEvent(mortgageExternalId, request);
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }
}
