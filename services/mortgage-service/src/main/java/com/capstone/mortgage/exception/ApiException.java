package com.capstone.mortgage.exception;

import org.springframework.http.HttpStatus;

/** Base type for exceptions that map directly to the standard error envelope. */
public abstract class ApiException extends RuntimeException {

    private final String code;
    private final HttpStatus status;

    protected ApiException(String code, HttpStatus status, String message) {
        super(message);
        this.code = code;
        this.status = status;
    }

    public String getCode() { return code; }
    public HttpStatus getStatus() { return status; }
}
