package com.capstone.mortgage.controller;

import com.capstone.mortgage.dto.BorrowerRequest;
import com.capstone.mortgage.dto.BorrowerResponse;
import com.capstone.mortgage.service.BorrowerService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/borrowers")
public class BorrowerController {

    private final BorrowerService borrowerService;

    public BorrowerController(BorrowerService borrowerService) {
        this.borrowerService = borrowerService;
    }

    @PostMapping
    public ResponseEntity<BorrowerResponse> create(@Valid @RequestBody BorrowerRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(borrowerService.create(request));
    }

    @GetMapping("/{borrowerExternalId}")
    public BorrowerResponse get(@PathVariable String borrowerExternalId) {
        return borrowerService.getByExternalId(borrowerExternalId);
    }
}
