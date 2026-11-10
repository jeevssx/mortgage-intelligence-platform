package com.capstone.servicing.lookup;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.dynamodb.DynamoDbClient;
import software.amazon.awssdk.services.dynamodb.DynamoDbClientBuilder;
import software.amazon.awssdk.services.dynamodb.model.*;

import java.math.BigDecimal;
import java.net.URI;
import java.util.Map;
import java.util.Optional;

/**
 * DynamoDB-backed fast lookup cache (M8 task 8.4), write-through from SqsEventConsumer.
 *
 * Partition key is {@code mortgageExternalId} (one item per key, uniform distribution) rather
 * than {@code borrowerExternalId} — grouping by borrower would skew partition sizes as
 * borrowers accumulate different numbers of mortgages over time, and a bulk load of many
 * mortgages for the same borrower would all land on one partition. mortgageExternalId gives
 * DynamoDB's internal hashing one item per key to spread evenly, with no such skew.
 *
 * No-ops (write-through and lookups both skipped) if DYNAMODB_TABLE_MORTGAGE_LOOKUP is unset —
 * used in tests and any environment without this table provisioned.
 */
@Component
public class MortgageLookupRepository {

    private static final Logger log = LoggerFactory.getLogger(MortgageLookupRepository.class);

    private final String tableName;
    private final DynamoDbClient client;

    @Autowired
    public MortgageLookupRepository(Environment env) {
        this.tableName = env.getProperty("capstone.lookup.dynamodb-table-mortgage-lookup");
        this.client = buildClient(env);
    }

    /** Test-only seam — injects an already-built (mock) client instead of one built from env. */
    MortgageLookupRepository(String tableName, DynamoDbClient client) {
        this.tableName = tableName;
        this.client = client;
    }

    private DynamoDbClient buildClient(Environment env) {
        if (!StringUtils.hasText(tableName)) {
            return null;
        }
        String region = env.getProperty("capstone.messaging.aws-region", "us-east-1");
        String endpointUrl = env.getProperty("capstone.messaging.aws-endpoint-url");

        DynamoDbClientBuilder builder = DynamoDbClient.builder().region(Region.of(region));
        if (StringUtils.hasText(endpointUrl)) {
            builder.endpointOverride(URI.create(endpointUrl))
                    .credentialsProvider(StaticCredentialsProvider.create(
                            AwsBasicCredentials.create("test", "test")));
        } else {
            builder.credentialsProvider(DefaultCredentialsProvider.create());
        }
        return builder.build();
    }

    public boolean isEnabled() {
        return client != null;
    }

    public void upsert(MortgageLookupRecord record) {
        if (client == null) {
            return;
        }
        try {
            client.putItem(PutItemRequest.builder()
                    .tableName(tableName)
                    .item(Map.of(
                            "mortgageExternalId", AttributeValue.fromS(record.mortgageExternalId()),
                            "borrowerExternalId", AttributeValue.fromS(record.borrowerExternalId()),
                            "status", AttributeValue.fromS(record.status()),
                            "outstandingBalance", AttributeValue.fromN(record.outstandingBalance().toPlainString())))
                    .build());
        } catch (Exception ex) {
            log.error("DYNAMODB_WRITE_FAILED mortgageExternalId={}", record.mortgageExternalId(), ex);
        }
    }

    public void updateBalance(String mortgageExternalId, BigDecimal newBalance) {
        updateAttribute(mortgageExternalId, "outstandingBalance", AttributeValue.fromN(newBalance.toPlainString()));
    }

    public void updateStatus(String mortgageExternalId, String newStatus) {
        updateAttribute(mortgageExternalId, "status", AttributeValue.fromS(newStatus));
    }

    private void updateAttribute(String mortgageExternalId, String attribute, AttributeValue value) {
        if (client == null) {
            return;
        }
        try {
            client.updateItem(UpdateItemRequest.builder()
                    .tableName(tableName)
                    .key(Map.of("mortgageExternalId", AttributeValue.fromS(mortgageExternalId)))
                    .attributeUpdates(Map.of(attribute, AttributeValueUpdate.builder().value(value).action(AttributeAction.PUT).build()))
                    .build());
        } catch (Exception ex) {
            log.error("DYNAMODB_UPDATE_FAILED mortgageExternalId={} attribute={}", mortgageExternalId, attribute, ex);
        }
    }

    public Optional<MortgageLookupRecord> find(String mortgageExternalId) {
        if (client == null) {
            return Optional.empty();
        }
        GetItemResponse response = client.getItem(GetItemRequest.builder()
                .tableName(tableName)
                .key(Map.of("mortgageExternalId", AttributeValue.fromS(mortgageExternalId)))
                .build());
        if (!response.hasItem() || response.item().isEmpty()) {
            return Optional.empty();
        }
        Map<String, AttributeValue> item = response.item();
        return Optional.of(new MortgageLookupRecord(
                item.get("mortgageExternalId").s(),
                item.get("borrowerExternalId").s(),
                item.get("status").s(),
                new BigDecimal(item.get("outstandingBalance").n())));
    }
}
