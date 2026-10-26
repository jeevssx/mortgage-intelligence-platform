package com.capstone.mortgage.entity;

/** Mirrors the payment.status CHECK constraint in database/migrations/001_core_schema.sql. */
public enum PaymentStatus {
    SCHEDULED,
    POSTED,
    FAILED,
    REVERSED
}
