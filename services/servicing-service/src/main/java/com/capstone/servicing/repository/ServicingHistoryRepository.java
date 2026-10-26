package com.capstone.servicing.repository;

import com.capstone.servicing.entity.Mortgage;
import com.capstone.servicing.entity.ServicingHistory;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ServicingHistoryRepository extends JpaRepository<ServicingHistory, java.util.UUID> {
    List<ServicingHistory> findByMortgageOrderByEventTimeAsc(Mortgage mortgage);
}
