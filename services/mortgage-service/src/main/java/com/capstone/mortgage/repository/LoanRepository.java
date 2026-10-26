package com.capstone.mortgage.repository;

import com.capstone.mortgage.entity.Loan;
import com.capstone.mortgage.entity.Mortgage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface LoanRepository extends JpaRepository<Loan, UUID> {
    Optional<Loan> findByLoanExternalId(String loanExternalId);
    boolean existsByLoanExternalId(String loanExternalId);
    Optional<Loan> findByMortgage(Mortgage mortgage);
}
