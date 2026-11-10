package com.capstone.servicing.messaging;

import com.capstone.servicing.entity.EventInbox;
import com.capstone.servicing.lookup.MortgageLookupRecord;
import com.capstone.servicing.lookup.MortgageLookupRepository;
import com.capstone.servicing.repository.EventInboxRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import software.amazon.awssdk.services.sqs.SqsClient;
import software.amazon.awssdk.services.sqs.model.DeleteMessageRequest;
import software.amazon.awssdk.services.sqs.model.Message;

import java.math.BigDecimal;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit coverage for handle() — the dedupe/write-through/force-failure logic that was previously
 * only exercised ad hoc against live LocalStack (M5/M8), never asserted in an automated test.
 * poll() itself (the @Scheduled loop) is intentionally not unit-tested — it's a thin wrapper
 * whose only real behavior (polling LocalStack SQS) was live-verified in M5/M8.
 */
class SqsEventConsumerTest {

    private static final String QUEUE_URL = "http://localstack:4566/000000000000/capstone-mortgage-servicing-dev";

    private EventInboxRepository eventInboxRepository = mock(EventInboxRepository.class);
    private MortgageLookupRepository lookupRepository = mock(MortgageLookupRepository.class);
    private SqsClient sqsClient = mock(SqsClient.class);
    private SqsEventConsumer consumer = new SqsEventConsumer(
            new ObjectMapper(), eventInboxRepository, lookupRepository, QUEUE_URL, sqsClient);

    private Message message(String body) {
        return Message.builder().messageId("msg-1").receiptHandle("rh-1").body(body).build();
    }

    @Test
    void handle_newEvent_savesToInboxAndAcksMessage() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(false);
        when(lookupRepository.isEnabled()).thenReturn(false);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"LoanApproved","payload":{"mortgageExternalId":"MTG-1001"}}
                """.formatted(eventId)));

        ArgumentCaptor<EventInbox> captor = ArgumentCaptor.forClass(EventInbox.class);
        verify(eventInboxRepository).save(captor.capture());
        assertThat(captor.getValue().getEventId()).isEqualTo(eventId);
        assertThat(captor.getValue().getEventType()).isEqualTo("LoanApproved");

        ArgumentCaptor<DeleteMessageRequest> deleteCaptor = ArgumentCaptor.forClass(DeleteMessageRequest.class);
        verify(sqsClient).deleteMessage(deleteCaptor.capture());
        assertThat(deleteCaptor.getValue().queueUrl()).isEqualTo(QUEUE_URL);
        assertThat(deleteCaptor.getValue().receiptHandle()).isEqualTo("rh-1");
    }

    @Test
    void handle_duplicateEvent_skipsSaveButStillAcks() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(true);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"LoanApproved","payload":{}}
                """.formatted(eventId)));

        verify(eventInboxRepository, never()).save(any());
        verify(sqsClient).deleteMessage(any(DeleteMessageRequest.class));
    }

    @Test
    void handle_mortgageCreated_writesThroughAsUpsert() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(false);
        when(lookupRepository.isEnabled()).thenReturn(true);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"MortgageCreated","payload":
                  {"mortgageExternalId":"MTG-1001","borrowerExternalId":"BOR-001","status":"ACTIVE","originalAmount":"250000.00"}}
                """.formatted(eventId)));

        ArgumentCaptor<MortgageLookupRecord> captor = ArgumentCaptor.forClass(MortgageLookupRecord.class);
        verify(lookupRepository).upsert(captor.capture());
        assertThat(captor.getValue().mortgageExternalId()).isEqualTo("MTG-1001");
        assertThat(captor.getValue().outstandingBalance()).isEqualTo(new BigDecimal("250000.00"));
    }

    @Test
    void handle_paymentReceived_writesThroughAsBalanceUpdate() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(false);
        when(lookupRepository.isEnabled()).thenReturn(true);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"PaymentReceived","payload":
                  {"mortgageExternalId":"MTG-1001","outstandingBalanceAfter":"248150.00"}}
                """.formatted(eventId)));

        verify(lookupRepository).updateBalance("MTG-1001", new BigDecimal("248150.00"));
    }

    @Test
    void handle_loanDelinquent_writesThroughAsStatusUpdate() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(false);
        when(lookupRepository.isEnabled()).thenReturn(true);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"LoanDelinquent","payload":{"mortgageExternalId":"MTG-1002"}}
                """.formatted(eventId)));

        verify(lookupRepository).updateStatus("MTG-1002", "DELINQUENT");
    }

    @Test
    void handle_lookupDisabled_neverCallsLookupRepositoryWrites() throws Exception {
        UUID eventId = UUID.randomUUID();
        when(eventInboxRepository.existsById(eventId)).thenReturn(false);
        when(lookupRepository.isEnabled()).thenReturn(false);

        consumer.handle(message("""
                {"eventId":"%s","eventType":"MortgageCreated","payload":{"mortgageExternalId":"MTG-1001"}}
                """.formatted(eventId)));

        verify(lookupRepository, never()).upsert(any());
    }

    @Test
    void handle_forceFailureDrill_throwsWithoutAckingOrSaving() {
        UUID eventId = UUID.randomUUID();

        assertThatThrownBy(() -> consumer.handle(message("""
                {"eventId":"%s","eventType":"FORCE_FAILURE_TEST","payload":{}}
                """.formatted(eventId))))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Forced failure drill");

        verifyNoInteractions(eventInboxRepository);
        verify(sqsClient, never()).deleteMessage(any(DeleteMessageRequest.class));
    }
}
