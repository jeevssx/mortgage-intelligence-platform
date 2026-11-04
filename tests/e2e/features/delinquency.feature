Feature: Missed payment -> delinquency state (Journey 3)
  # US-DEL-001 (docs/requirements/user-stories.md). MTG-1002 is seeded DELINQUENT,
  # 45 days past due since 2026-01-10 (database/README.md demo IDs) — this journey asserts the
  # 30-day rule's outcome rather than re-running the 30-day clock itself.

  Background:
    Given the user "servicing" is authenticated

  Scenario: A mortgage past the 30-day rule shows as delinquent with the expected details
    When the user requests delinquency status for mortgage "MTG-1002"
    Then the response status should be 200
    And the delinquency status should be "DELINQUENT"
    And the days past due should be at least 30
    And the severity should be "MODERATE"

  Scenario: A current mortgage has no delinquency record
    When the user requests delinquency status for mortgage "MTG-1001"
    Then the response status should be 404
    And the error code should be "DELINQUENCY_NOT_FOUND"
