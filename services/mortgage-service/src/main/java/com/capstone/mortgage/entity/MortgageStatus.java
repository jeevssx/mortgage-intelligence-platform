package com.capstone.mortgage.entity;

/** Mirrors the mortgage.status CHECK constraint in database/migrations/001_core_schema.sql. */
public enum MortgageStatus {
    PENDING,
    ACTIVE,
    DELINQUENT,
    CLOSED
}
