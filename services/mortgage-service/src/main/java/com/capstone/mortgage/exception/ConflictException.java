package com.capstone.mortgage.exception;

import org.springframework.http.HttpStatus;

public class ConflictException extends ApiException {
    public ConflictException(String code, String message) {
        super(code, HttpStatus.CONFLICT, message);
    }
}
