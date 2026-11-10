package com.capstone.mortgage.repository;

import com.capstone.mortgage.entity.Mortgage;
import com.capstone.mortgage.entity.ServicingHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface ServicingHistoryRepository extends JpaRepository<ServicingHistory, UUID> {
    long countByMortgage(Mortgage mortgage);
}
