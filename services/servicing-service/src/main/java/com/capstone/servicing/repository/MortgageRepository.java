package com.capstone.servicing.repository;

import com.capstone.servicing.entity.Mortgage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface MortgageRepository extends JpaRepository<Mortgage, UUID> {
    Optional<Mortgage> findByMortgageExternalId(String mortgageExternalId);
}
