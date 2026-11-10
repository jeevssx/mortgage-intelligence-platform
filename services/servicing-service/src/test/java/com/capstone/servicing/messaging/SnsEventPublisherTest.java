package com.capstone.servicing.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import software.amazon.awssdk.services.sns.SnsClient;
import software.amazon.awssdk.services.sns.model.PublishRequest;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class SnsEventPublisherTest {

    private static final String TOPIC_ARN = "arn:aws:sns:us-east-1:000000000000:capstone-mortgage-lifecycle-dev";

    // Spring Boot's auto-configured ObjectMapper bean registers JavaTimeModule automatically
    // (EventEnvelope.occurredAt is an OffsetDateTime); a bare `new ObjectMapper()` can't
    // serialize it and publish()'s try/catch would silently swallow that failure.
    private static ObjectMapper objectMapper() {
        return new ObjectMapper().registerModule(new JavaTimeModule());
    }

    @Test
    void disabled_whenNoTopicConfigured_publishIsASafeNoOp() {
        SnsEventPublisher publisher = new SnsEventPublisher(new ObjectMapper(), (String) null, null);
        publisher.publish(EventEnvelope.of("LoanDelinquent", "corr-1", Map.of("mortgageExternalId", "MTG-1001")));
        // No exception, no client call possible (client is null) — proves the null-guard path.
    }

    @Test
    void publish_whenEnabled_sendsTopicArnAndEventTypeAttribute() {
        SnsClient client = mock(SnsClient.class);
        SnsEventPublisher publisher = new SnsEventPublisher(objectMapper(), TOPIC_ARN, client);
        EventEnvelope event = EventEnvelope.of("LoanDelinquent", "corr-1", Map.of("mortgageExternalId", "MTG-1001"));

        publisher.publish(event);

        ArgumentCaptor<PublishRequest> captor = ArgumentCaptor.forClass(PublishRequest.class);
        verify(client).publish(captor.capture());
        PublishRequest request = captor.getValue();
        assertThat(request.topicArn()).isEqualTo(TOPIC_ARN);
        assertThat(request.message()).contains("LoanDelinquent").contains("MTG-1001");
        assertThat(request.messageAttributes().get("eventType").stringValue()).isEqualTo("LoanDelinquent");
    }

    @Test
    void publish_whenClientThrows_isSwallowedNotPropagated() {
        SnsClient client = mock(SnsClient.class);
        when(client.publish(any(PublishRequest.class))).thenThrow(new RuntimeException("boom"));
        SnsEventPublisher publisher = new SnsEventPublisher(objectMapper(), TOPIC_ARN, client);

        publisher.publish(EventEnvelope.of("LoanDelinquent", "corr-1", Map.of("mortgageExternalId", "MTG-1001")));
        // No exception propagated — a down SNS topic must never fail the caller's request.
    }
}
