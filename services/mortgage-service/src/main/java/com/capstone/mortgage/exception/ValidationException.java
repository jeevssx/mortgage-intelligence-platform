package com.capstone.mortgage.exception;

import org.springframework.http.HttpStatus;

public class ValidationException extends ApiException {
    public ValidationException(String code, String message) {
        super(code, HttpStatus.BAD_REQUEST, message);
    }
}
