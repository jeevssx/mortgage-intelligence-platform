package com.capstone.mortgage.mapper;

import com.capstone.mortgage.dto.BorrowerRequest;
import com.capstone.mortgage.dto.BorrowerResponse;
import com.capstone.mortgage.entity.Borrower;

public final class BorrowerMapper {

    private BorrowerMapper() { }

    public static Borrower toEntity(BorrowerRequest request) {
        Borrower borrower = new Borrower();
        borrower.setBorrowerExternalId(request.borrowerExternalId());
        borrower.setFirstName(request.firstName());
        borrower.setLastName(request.lastName());
        borrower.setEmail(request.email());
        borrower.setPhone(request.phone());
        borrower.setDateOfBirth(request.dateOfBirth());
        return borrower;
    }

    public static BorrowerResponse toResponse(Borrower borrower) {
        return new BorrowerResponse(
                borrower.getId(),
                borrower.getBorrowerExternalId(),
                borrower.getFirstName(),
                borrower.getLastName(),
                borrower.getEmail(),
                borrower.getPhone(),
                borrower.getDateOfBirth()
        );
    }
}
