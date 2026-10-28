Feature: Payment posting -> servicing history visible (Journey 2)
  # US-PAY-001, US-SRV-001 (docs/requirements/user-stories.md)

  Background:
    Given the user "servicing" is authenticated

  Scenario: Posting a payment reduces the balance and appears in servicing history
    When the user posts a payment of "1850.00" on mortgage "MTG-1001"
    Then the response status should be 201
    And the outstanding balance should have decreased by "1850.00"
    When the user requests servicing history for mortgage "MTG-1001"
    Then the response status should be 200
    And the servicing history should include a "PAYMENT_POSTED" event

  Scenario: Posting a payment with a non-positive amount is rejected
    When the user posts a payment of "-5.00" on mortgage "MTG-1001"
    Then the response status should be 400
    And the error code should be "VALIDATION_FAILED"

  Scenario: Servicing history for an unknown mortgage returns 404
    When the user requests servicing history for mortgage "MTG-9999"
    Then the response status should be 404
    And the error code should be "MORTGAGE_NOT_FOUND"
