package com.capstone.mortgage.configuration;

/** Request-scoped correlation ID, set by {@link CorrelationIdFilter}. */
public final class CorrelationIdHolder {

    public static final String HEADER = "X-Correlation-Id";
    private static final ThreadLocal<String> CURRENT = new ThreadLocal<>();

    private CorrelationIdHolder() { }

    public static void set(String correlationId) {
        CURRENT.set(correlationId);
    }

    public static String get() {
        return CURRENT.get();
    }

    public static void clear() {
        CURRENT.remove();
    }
}
