package com.capstone.mortgage.mapper;

import com.capstone.mortgage.dto.MortgageResponse;
import com.capstone.mortgage.entity.Loan;
import com.capstone.mortgage.entity.Mortgage;

public final class MortgageMapper {

    private MortgageMapper() { }

    public static MortgageResponse toResponse(Mortgage mortgage, Loan loan) {
        return new MortgageResponse(
                mortgage.getId(),
                mortgage.getMortgageExternalId(),
                mortgage.getBorrower().getBorrowerExternalId(),
                mortgage.getStatus(),
                mortgage.getOriginalAmount(),
                mortgage.getOutstandingBalance(),
                mortgage.getOriginationDate(),
                LoanMapper.toResponse(loan)
        );
    }
}
