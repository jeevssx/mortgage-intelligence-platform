package com.capstone.servicing.messaging;

public interface EventPublisher {
    void publish(EventEnvelope event);
}
