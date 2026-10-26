package com.capstone.mortgage.repository;

import com.capstone.mortgage.entity.Borrower;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface BorrowerRepository extends JpaRepository<Borrower, UUID> {
    Optional<Borrower> findByBorrowerExternalId(String borrowerExternalId);
    boolean existsByBorrowerExternalId(String borrowerExternalId);
}
