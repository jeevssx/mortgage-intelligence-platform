package com.capstone.mortgage.controller;

import com.capstone.mortgage.dto.MortgageRequest;
import com.capstone.mortgage.dto.MortgageResponse;
import com.capstone.mortgage.dto.PageResponse;
import com.capstone.mortgage.service.MortgageService;
import jakarta.validation.Valid;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/mortgages")
public class MortgageController {

    private final MortgageService mortgageService;

    public MortgageController(MortgageService mortgageService) {
        this.mortgageService = mortgageService;
    }

    @PostMapping
    @PreAuthorize("hasAnyAuthority('ADMIN', 'UNDERWRITER')")
    public ResponseEntity<MortgageResponse> create(@Valid @RequestBody MortgageRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(mortgageService.create(request));
    }

    @GetMapping("/{mortgageExternalId}")
    public MortgageResponse get(@PathVariable String mortgageExternalId) {
        return mortgageService.getByExternalId(mortgageExternalId);
    }

    @GetMapping
    public PageResponse<MortgageResponse> list(
            @RequestParam(required = false) String borrowerId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Pageable pageable = PageRequest.of(page, size);
        return mortgageService.list(borrowerId, pageable);
    }
}
