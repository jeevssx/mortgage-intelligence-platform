package com.capstone.servicing.lookup;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.model.*;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit coverage for the DynamoDB write-through paths, found uncovered (0% on the enabled branch)
 * while measuring real coverage for M10's test-strategy.md — everything here was previously
 * exercised only ad hoc against live LocalStack in M8, never asserted in an automated test.
 */
class MortgageLookupRepositoryTest {

    private static final String TABLE = "MortgageLookup-dev";

    @Test
    void disabled_whenNoTableConfigured_allOperationsAreSafeNoOps() {
        MortgageLookupRepository repo = new MortgageLookupRepository((String) null, null);

        assertThat(repo.isEnabled()).isFalse();
        repo.upsert(new MortgageLookupRecord("MTG-1", "BOR-1", "ACTIVE", BigDecimal.TEN));
        repo.updateBalance("MTG-1", BigDecimal.ONE);
        repo.updateStatus("MTG-1", "DELINQUENT");
        assertThat(repo.find("MTG-1")).isEmpty();
    }

    @Test
    void upsert_whenEnabled_putsAllFourAttributes() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        repo.upsert(new MortgageLookupRecord("MTG-1001", "BOR-001", "ACTIVE", new BigDecimal("250000.00")));

        ArgumentCaptor<PutItemRequest> captor = ArgumentCaptor.forClass(PutItemRequest.class);
        verify(client).putItem(captor.capture());
        PutItemRequest request = captor.getValue();
        assertThat(request.tableName()).isEqualTo(TABLE);
        assertThat(request.item().get("mortgageExternalId").s()).isEqualTo("MTG-1001");
        assertThat(request.item().get("borrowerExternalId").s()).isEqualTo("BOR-001");
        assertThat(request.item().get("status").s()).isEqualTo("ACTIVE");
        assertThat(request.item().get("outstandingBalance").n()).isEqualTo("250000.00");
    }

    @Test
    void upsert_whenClientThrows_isSwallowedNotPropagated() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        when(client.putItem(any(PutItemRequest.class))).thenThrow(new RuntimeException("boom"));
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        repo.upsert(new MortgageLookupRecord("MTG-1001", "BOR-001", "ACTIVE", BigDecimal.ZERO));
        // No exception propagated — write-through is best-effort, never blocks the SQS consumer.
    }

    @Test
    void updateBalance_sendsUpdateItemWithNumericAttribute() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        repo.updateBalance("MTG-1001", new BigDecimal("1200.50"));

        ArgumentCaptor<UpdateItemRequest> captor = ArgumentCaptor.forClass(UpdateItemRequest.class);
        verify(client).updateItem(captor.capture());
        UpdateItemRequest request = captor.getValue();
        assertThat(request.key().get("mortgageExternalId").s()).isEqualTo("MTG-1001");
        assertThat(request.attributeUpdates().get("outstandingBalance").value().n()).isEqualTo("1200.50");
    }

    @Test
    void updateStatus_sendsUpdateItemWithStringAttribute() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        repo.updateStatus("MTG-1001", "DELINQUENT");

        ArgumentCaptor<UpdateItemRequest> captor = ArgumentCaptor.forClass(UpdateItemRequest.class);
        verify(client).updateItem(captor.capture());
        assertThat(captor.getValue().attributeUpdates().get("status").value().s()).isEqualTo("DELINQUENT");
    }

    @Test
    void find_whenItemExists_mapsAllFields() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        GetItemResponse response = GetItemResponse.builder()
                .item(Map.of(
                        "mortgageExternalId", AttributeValue.fromS("MTG-1001"),
                        "borrowerExternalId", AttributeValue.fromS("BOR-001"),
                        "status", AttributeValue.fromS("ACTIVE"),
                        "outstandingBalance", AttributeValue.fromN("250000.00")))
                .build();
        when(client.getItem(any(GetItemRequest.class))).thenReturn(response);
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        Optional<MortgageLookupRecord> result = repo.find("MTG-1001");

        assertThat(result).isPresent();
        assertThat(result.get().borrowerExternalId()).isEqualTo("BOR-001");
        assertThat(result.get().outstandingBalance()).isEqualTo(new BigDecimal("250000.00"));
    }

    @Test
    void find_whenItemMissing_returnsEmpty() {
        DynamoDbClient client = mock(DynamoDbClient.class);
        when(client.getItem(any(GetItemRequest.class))).thenReturn(GetItemResponse.builder().build());
        MortgageLookupRepository repo = new MortgageLookupRepository(TABLE, client);

        assertThat(repo.find("MTG-9999")).isEmpty();
    }
}
