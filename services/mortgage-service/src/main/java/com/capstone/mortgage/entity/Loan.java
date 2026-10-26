package com.capstone.mortgage.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "loan")
public class Loan {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "loan_external_id", nullable = false, unique = true, length = 20)
    private String loanExternalId;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "mortgage_id", nullable = false, unique = true)
    private Mortgage mortgage;

    @Column(name = "interest_rate", nullable = false, precision = 6, scale = 4)
    private BigDecimal interestRate;

    @Column(name = "term_months", nullable = false)
    private Integer termMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "underwriting_decision", nullable = false, length = 20)
    private UnderwritingDecision underwritingDecision;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getLoanExternalId() { return loanExternalId; }
    public void setLoanExternalId(String loanExternalId) { this.loanExternalId = loanExternalId; }

    public Mortgage getMortgage() { return mortgage; }
    public void setMortgage(Mortgage mortgage) { this.mortgage = mortgage; }

    public BigDecimal getInterestRate() { return interestRate; }
    public void setInterestRate(BigDecimal interestRate) { this.interestRate = interestRate; }

    public Integer getTermMonths() { return termMonths; }
    public void setTermMonths(Integer termMonths) { this.termMonths = termMonths; }

    public UnderwritingDecision getUnderwritingDecision() { return underwritingDecision; }
    public void setUnderwritingDecision(UnderwritingDecision underwritingDecision) { this.underwritingDecision = underwritingDecision; }

    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
