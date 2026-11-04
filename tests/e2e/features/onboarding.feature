Feature: Borrower -> mortgage onboarding (Journey 1)
  # US-BOR-001, US-MTG-001 (docs/requirements/user-stories.md)

  Scenario: Underwriter creates a borrower and a mortgage for them
    Given the user "underwriter" is authenticated
    When the user creates a new borrower
    Then the response status should be 201
    When the user creates a new mortgage for that borrower with an approved loan
    Then the response status should be 201
    And the mortgage status should be "ACTIVE"

  Scenario: Creating a mortgage for an unknown borrower fails cleanly
    Given the user "underwriter" is authenticated
    When the user creates a mortgage for borrower "BOR-999" which does not exist
    Then the response status should be 404
    And the error code should be "BORROWER_NOT_FOUND"
