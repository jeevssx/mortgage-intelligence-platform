package com.capstone.mortgage.exception;

import com.capstone.mortgage.configuration.CorrelationIdHolder;
import com.capstone.mortgage.dto.ErrorResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorResponse> handleApiException(ApiException ex) {
        String correlationId = CorrelationIdHolder.get();
        log.warn("{} ({}) correlationId={}", ex.getCode(), ex.getMessage(), correlationId);
        return ResponseEntity.status(ex.getStatus())
                .body(ErrorResponse.of(ex.getCode(), ex.getMessage(), correlationId));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        String correlationId = CorrelationIdHolder.get();
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(err -> err.getField() + ": " + fieldMessage(err))
                .collect(Collectors.joining("; "));
        log.warn("VALIDATION_FAILED ({}) correlationId={}", message, correlationId);
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(ErrorResponse.of("VALIDATION_FAILED", message, correlationId));
    }

    // @PreAuthorize throws these during the controller method invocation itself (AOP around the
    // handler), which DispatcherServlet resolves via @ExceptionHandler *before* the exception
    // can reach Spring Security's filter-level ExceptionTranslationFilter/AccessDeniedHandler.
    // Without these two handlers, the generic Exception.class one below would turn every 401/403
    // into a 500.
    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAccessDenied(AccessDeniedException ex) {
        String correlationId = CorrelationIdHolder.get();
        log.warn("FORBIDDEN ({}) correlationId={}", ex.getMessage(), correlationId);
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ErrorResponse.of("FORBIDDEN", "Role does not permit this operation", correlationId));
    }

    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<ErrorResponse> handleAuthentication(AuthenticationException ex) {
        String correlationId = CorrelationIdHolder.get();
        log.warn("UNAUTHORIZED ({}) correlationId={}", ex.getMessage(), correlationId);
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ErrorResponse.of("UNAUTHORIZED", "Missing or invalid Bearer token", correlationId));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        String correlationId = CorrelationIdHolder.get();
        log.error("UNEXPECTED_ERROR correlationId={}", correlationId, ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorResponse.of("INTERNAL_ERROR", "An unexpected error occurred", correlationId));
    }

    private static String fieldMessage(FieldError err) {
        return err.getDefaultMessage() == null ? "invalid" : err.getDefaultMessage();
    }
}
