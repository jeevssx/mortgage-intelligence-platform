package com.capstone.mortgage.messaging;

public interface EventPublisher {
    void publish(EventEnvelope event);
}
