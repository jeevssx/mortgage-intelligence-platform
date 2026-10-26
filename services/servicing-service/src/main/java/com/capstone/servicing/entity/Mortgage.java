package com.capstone.servicing.entity;

import jakarta.persistence.*;
import java.util.UUID;

/** Read-mostly view of the mortgage table. Owned (written) by mortgage-service; see docs/adr/ADR-001. */
@Entity
@Table(name = "mortgage")
public class Mortgage {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "mortgage_external_id", nullable = false, unique = true, length = 20)
    private String mortgageExternalId;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private MortgageStatus status;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getMortgageExternalId() { return mortgageExternalId; }
    public void setMortgageExternalId(String mortgageExternalId) { this.mortgageExternalId = mortgageExternalId; }

    public MortgageStatus getStatus() { return status; }
    public void setStatus(MortgageStatus status) { this.status = status; }
}
