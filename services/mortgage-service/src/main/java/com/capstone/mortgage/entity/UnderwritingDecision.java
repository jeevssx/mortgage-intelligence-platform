package com.capstone.mortgage.entity;

/** Mirrors the loan.underwriting_decision CHECK constraint in database/migrations/001_core_schema.sql. */
public enum UnderwritingDecision {
    PENDING,
    APPROVED,
    DECLINED
}
