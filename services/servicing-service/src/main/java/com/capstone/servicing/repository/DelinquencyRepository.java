package com.capstone.servicing.repository;

import com.capstone.servicing.entity.Delinquency;
import com.capstone.servicing.entity.Mortgage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface DelinquencyRepository extends JpaRepository<Delinquency, UUID> {
    Optional<Delinquency> findByMortgage(Mortgage mortgage);
}
