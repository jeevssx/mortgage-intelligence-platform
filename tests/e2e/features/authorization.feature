Feature: Role-based access control (Journey 4)
  # US-SEC-001 (docs/requirements/user-stories.md)

  Scenario: Requests without a token are rejected
    When an unauthenticated user requests mortgage "MTG-1001"
    Then the response status should be 401

  Scenario: A SUPPORT user cannot post a payment
    Given the user "support" is authenticated
    When the user posts a payment of "100.00" on mortgage "MTG-1001"
    Then the response status should be 403
    And the error code should be "FORBIDDEN"

  Scenario: An ADMIN user can post a payment (control case — the deny above is role-specific, not universal)
    Given the user "admin" is authenticated
    When the user posts a payment of "100.00" on mortgage "MTG-1001"
    Then the response status should be 201
