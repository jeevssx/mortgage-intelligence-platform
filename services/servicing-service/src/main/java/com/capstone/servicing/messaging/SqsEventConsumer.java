package com.capstone.servicing.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.capstone.servicing.entity.EventInbox;
import com.capstone.servicing.lookup.MortgageLookupRecord;
import com.capstone.servicing.lookup.MortgageLookupRepository;
import com.capstone.servicing.repository.EventInboxRepository;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sqs.SqsClient;
import software.amazon.awssdk.services.sqs.SqsClientBuilder;
import software.amazon.awssdk.services.sqs.model.DeleteMessageRequest;
import software.amazon.awssdk.services.sqs.model.Message;
import software.amazon.awssdk.services.sqs.model.ReceiveMessageRequest;

import java.net.URI;
import java.util.List;
import java.util.UUID;

/**
 * Polls capstone-mortgage-servicing-dev for lifecycle events and records each eventId into
 * event_inbox (idempotent dedupe). See docs/architecture/event-catalog.md and the "Why events
 * don't replace the M4 direct writes" note in ADR-002 for why this doesn't also write
 * servicing_history. eventType=FORCE_FAILURE_TEST is a reserved drill value that always throws
 * without acking, to demonstrate the DLQ path (docs/operations/messaging-runbook.md).
 */
@Component
public class SqsEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(SqsEventConsumer.class);
    private static final String FORCE_FAILURE_EVENT_TYPE = "FORCE_FAILURE_TEST";

    private final ObjectMapper objectMapper;
    private final EventInboxRepository eventInboxRepository;
    private final MortgageLookupRepository lookupRepository;
    private final String queueUrl;
    private final SqsClient sqsClient;

    @Autowired
    public SqsEventConsumer(ObjectMapper objectMapper, EventInboxRepository eventInboxRepository,
                             MortgageLookupRepository lookupRepository, Environment env) {
        this.objectMapper = objectMapper;
        this.eventInboxRepository = eventInboxRepository;
        this.lookupRepository = lookupRepository;
        this.queueUrl = env.getProperty("capstone.messaging.sqs-queue-servicing-events");
        this.sqsClient = buildClient(env);
    }

    /** Test-only seam — injects an already-built (mock) client instead of one built from env. */
    SqsEventConsumer(ObjectMapper objectMapper, EventInboxRepository eventInboxRepository,
                      MortgageLookupRepository lookupRepository, String queueUrl, SqsClient sqsClient) {
        this.objectMapper = objectMapper;
        this.eventInboxRepository = eventInboxRepository;
        this.lookupRepository = lookupRepository;
        this.queueUrl = queueUrl;
        this.sqsClient = sqsClient;
    }

    private SqsClient buildClient(Environment env) {
        if (!StringUtils.hasText(queueUrl)) {
            return null;
        }
        String region = env.getProperty("capstone.messaging.aws-region", "us-east-1");
        String endpointUrl = env.getProperty("capstone.messaging.aws-endpoint-url");

        SqsClientBuilder builder = SqsClient.builder().region(Region.of(region));
        if (StringUtils.hasText(endpointUrl)) {
            builder.endpointOverride(URI.create(endpointUrl))
                    .credentialsProvider(StaticCredentialsProvider.create(
                            AwsBasicCredentials.create("test", "test")));
        } else {
            builder.credentialsProvider(DefaultCredentialsProvider.create());
        }
        return builder.build();
    }

    @PostConstruct
    void logReadiness() {
        if (sqsClient == null) {
            log.info("SQS_CONSUMER_DISABLED (no SQS_QUEUE_SERVICING_EVENTS configured)");
        } else {
            log.info("SQS_CONSUMER_READY queueUrl={}", queueUrl);
        }
    }

    @Scheduled(fixedDelayString = "${capstone.messaging.poll-delay-ms:2000}")
    public void poll() {
        if (sqsClient == null) {
            return;
        }
        List<Message> messages = sqsClient.receiveMessage(ReceiveMessageRequest.builder()
                        .queueUrl(queueUrl)
                        .maxNumberOfMessages(10)
                        .waitTimeSeconds(5)
                        .build())
                .messages();

        for (Message message : messages) {
            try {
                handle(message);
            } catch (Exception ex) {
                log.error("EVENT_PROCESSING_FAILED messageId={}", message.messageId(), ex);
                // Do not delete: redelivered until maxReceiveCount, then routed to the DLQ.
            }
        }
    }

    // Each repository call below is transactional on its own (Spring Data JPA default);
    // existsById + save are not wrapped in one outer transaction because this method is called
    // via self-invocation from poll(), where a class-level @Transactional would silently no-op.
    void handle(Message message) throws Exception {
        JsonNode node = objectMapper.readTree(message.body());
        UUID eventId = UUID.fromString(node.get("eventId").asText());
        String eventType = node.get("eventType").asText();

        if (FORCE_FAILURE_EVENT_TYPE.equals(eventType)) {
            throw new IllegalStateException("Forced failure drill for eventId=" + eventId);
        }

        if (eventInboxRepository.existsById(eventId)) {
            log.info("Duplicate event ignored eventId={} eventType={}", eventId, eventType);
        } else {
            eventInboxRepository.save(new EventInbox(eventId, eventType));
            log.info("Processed event eventType={} eventId={}", eventType, eventId);
            writeThroughToLookup(eventType, node.get("payload"));
        }
        ackMessage(message);
    }

    /** M8 task 8.4: keeps MortgageLookup-dev in sync with the same events already flowing through
     * SQS, instead of adding a second write path. No-ops if DynamoDB isn't configured. */
    private void writeThroughToLookup(String eventType, JsonNode payload) {
        if (!lookupRepository.isEnabled() || payload == null) {
            return;
        }
        String mortgageExternalId = textOrNull(payload, "mortgageExternalId");
        if (mortgageExternalId == null) {
            return;
        }
        switch (eventType) {
            case "MortgageCreated" -> lookupRepository.upsert(new MortgageLookupRecord(
                    mortgageExternalId,
                    textOrNull(payload, "borrowerExternalId"),
                    textOrNull(payload, "status"),
                    decimalOrZero(payload, "originalAmount")));
            case "PaymentReceived" -> lookupRepository.updateBalance(
                    mortgageExternalId, decimalOrZero(payload, "outstandingBalanceAfter"));
            case "LoanDelinquent" -> lookupRepository.updateStatus(mortgageExternalId, "DELINQUENT");
            default -> { /* LoanApproved/PaymentMissed don't change a MortgageLookup field */ }
        }
    }

    private static String textOrNull(JsonNode payload, String field) {
        JsonNode value = payload.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private static java.math.BigDecimal decimalOrZero(JsonNode payload, String field) {
        JsonNode value = payload.get(field);
        return value == null || value.isNull() ? java.math.BigDecimal.ZERO : new java.math.BigDecimal(value.asText());
    }

    private void ackMessage(Message message) {
        sqsClient.deleteMessage(DeleteMessageRequest.builder()
                .queueUrl(queueUrl)
                .receiptHandle(message.receiptHandle())
                .build());
    }
}
