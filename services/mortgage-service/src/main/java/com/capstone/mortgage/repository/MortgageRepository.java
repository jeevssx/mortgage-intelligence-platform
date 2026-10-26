package com.capstone.mortgage.repository;

import com.capstone.mortgage.entity.Mortgage;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface MortgageRepository extends JpaRepository<Mortgage, UUID> {
    Optional<Mortgage> findByMortgageExternalId(String mortgageExternalId);
    boolean existsByMortgageExternalId(String mortgageExternalId);
    Page<Mortgage> findByBorrower_BorrowerExternalId(String borrowerExternalId, Pageable pageable);
}
