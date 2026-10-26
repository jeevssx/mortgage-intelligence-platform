package com.capstone.mortgage.service;

import com.capstone.mortgage.dto.BorrowerRequest;
import com.capstone.mortgage.dto.BorrowerResponse;
import com.capstone.mortgage.entity.Borrower;
import com.capstone.mortgage.exception.ConflictException;
import com.capstone.mortgage.exception.NotFoundException;
import com.capstone.mortgage.mapper.BorrowerMapper;
import com.capstone.mortgage.repository.BorrowerRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BorrowerServiceImpl implements BorrowerService {

    private final BorrowerRepository borrowerRepository;

    public BorrowerServiceImpl(BorrowerRepository borrowerRepository) {
        this.borrowerRepository = borrowerRepository;
    }

    @Override
    @Transactional
    public BorrowerResponse create(BorrowerRequest request) {
        if (borrowerRepository.existsByBorrowerExternalId(request.borrowerExternalId())) {
            throw new ConflictException("BORROWER_ALREADY_EXISTS",
                    "Borrower " + request.borrowerExternalId() + " already exists");
        }
        Borrower borrower = BorrowerMapper.toEntity(request);
        Borrower saved = borrowerRepository.save(borrower);
        return BorrowerMapper.toResponse(saved);
    }

    @Override
    @Transactional(readOnly = true)
    public BorrowerResponse getByExternalId(String borrowerExternalId) {
        Borrower borrower = borrowerRepository.findByBorrowerExternalId(borrowerExternalId)
                .orElseThrow(() -> new NotFoundException("BORROWER_NOT_FOUND",
                        "Borrower " + borrowerExternalId + " was not found"));
        return BorrowerMapper.toResponse(borrower);
    }
}
