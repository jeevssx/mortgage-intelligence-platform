package com.capstone.servicing.entity;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "delinquency")
public class Delinquency {

    @Id
    @GeneratedValue
    private UUID id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "mortgage_id", nullable = false, unique = true)
    private Mortgage mortgage;

    @Column(name = "delinquent_since", nullable = false)
    private LocalDate delinquentSince;

    @Column(name = "days_past_due", nullable = false)
    private Integer daysPastDue;

    @Enumerated(EnumType.STRING)
    @Column(name = "severity", nullable = false, length = 20)
    private DelinquencySeverity severity;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public Mortgage getMortgage() { return mortgage; }
    public void setMortgage(Mortgage mortgage) { this.mortgage = mortgage; }

    public LocalDate getDelinquentSince() { return delinquentSince; }
    public void setDelinquentSince(LocalDate delinquentSince) { this.delinquentSince = delinquentSince; }

    public Integer getDaysPastDue() { return daysPastDue; }
    public void setDaysPastDue(Integer daysPastDue) { this.daysPastDue = daysPastDue; }

    public DelinquencySeverity getSeverity() { return severity; }
    public void setSeverity(DelinquencySeverity severity) { this.severity = severity; }
}
