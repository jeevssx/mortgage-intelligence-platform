package com.capstone.servicing.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sns.SnsClient;
import software.amazon.awssdk.services.sns.SnsClientBuilder;
import software.amazon.awssdk.services.sns.model.MessageAttributeValue;
import software.amazon.awssdk.services.sns.model.PublishRequest;

import java.net.URI;
import java.util.Map;

/** Publishes LoanDelinquent to the shared lifecycle topic; no-ops if SNS_TOPIC_MORTGAGE_EVENTS is unset. */
@Component
public class SnsEventPublisher implements EventPublisher {

    private static final Logger log = LoggerFactory.getLogger(SnsEventPublisher.class);

    private final ObjectMapper objectMapper;
    private final String topicArn;
    private final SnsClient snsClient;

    public SnsEventPublisher(ObjectMapper objectMapper, Environment env) {
        this.objectMapper = objectMapper;
        this.topicArn = env.getProperty("capstone.messaging.sns-topic-mortgage-events");
        this.snsClient = buildClient(env);
    }

    private SnsClient buildClient(Environment env) {
        if (!StringUtils.hasText(topicArn)) {
            return null;
        }
        String region = env.getProperty("capstone.messaging.aws-region", "us-east-1");
        String endpointUrl = env.getProperty("capstone.messaging.aws-endpoint-url");

        SnsClientBuilder builder = SnsClient.builder().region(Region.of(region));
        if (StringUtils.hasText(endpointUrl)) {
            builder.endpointOverride(URI.create(endpointUrl))
                    .credentialsProvider(StaticCredentialsProvider.create(
                            AwsBasicCredentials.create("test", "test")));
        } else {
            builder.credentialsProvider(DefaultCredentialsProvider.create());
        }
        return builder.build();
    }

    @Override
    public void publish(EventEnvelope event) {
        if (snsClient == null) {
            log.debug("EVENT_PUBLISH_SKIPPED (no SNS topic configured) eventType={} eventId={}",
                    event.eventType(), event.eventId());
            return;
        }
        try {
            String body = objectMapper.writeValueAsString(event);
            snsClient.publish(PublishRequest.builder()
                    .topicArn(topicArn)
                    .message(body)
                    .messageAttributes(Map.of("eventType", MessageAttributeValue.builder()
                            .dataType("String")
                            .stringValue(event.eventType())
                            .build()))
                    .build());
            log.info("Published event eventType={} eventId={} correlationId={}",
                    event.eventType(), event.eventId(), event.correlationId());
        } catch (Exception ex) {
            log.error("EVENT_PUBLISH_FAILED eventType={} eventId={} correlationId={}",
                    event.eventType(), event.eventId(), event.correlationId(), ex);
        }
    }
}
