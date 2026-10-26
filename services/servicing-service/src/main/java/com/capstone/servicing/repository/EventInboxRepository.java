package com.capstone.servicing.repository;

import com.capstone.servicing.entity.EventInbox;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface EventInboxRepository extends JpaRepository<EventInbox, UUID> {
}
