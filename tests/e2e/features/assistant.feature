Feature: Mortgage question -> grounded RAG response with citation (Journey 5)
  # US-AI-001 (docs/requirements/user-stories.md). ai-assistant validates the same shared JWT
  # mortgage-service issues (docker-compose JWT_SECRET) rather than issuing its own tokens.

  Background:
    Given the user "underwriter" is authenticated

  Scenario: A policy question in the corpus returns a grounded answer with a citation
    When the user asks the assistant "What is the maximum debt-to-income ratio?"
    Then the response status should be 200
    And the assistant's citations should not be empty
    And requiresHumanApproval should be false

  Scenario: A question outside the corpus returns insufficient context, not a guess
    When the user asks the assistant "What is the weather forecast for tomorrow?"
    Then the response status should be 200
    And the assistant's citations should be empty
    And requiresHumanApproval should be true
