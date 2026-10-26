package com.capstone.mortgage.mapper;

import com.capstone.mortgage.dto.LoanRequest;
import com.capstone.mortgage.dto.LoanResponse;
import com.capstone.mortgage.entity.Loan;
import com.capstone.mortgage.entity.Mortgage;
import com.capstone.mortgage.entity.UnderwritingDecision;

public final class LoanMapper {

    private LoanMapper() { }

    public static Loan toEntity(LoanRequest request, Mortgage mortgage) {
        Loan loan = new Loan();
        loan.setLoanExternalId(request.loanExternalId());
        loan.setMortgage(mortgage);
        loan.setInterestRate(request.interestRate());
        loan.setTermMonths(request.termMonths());
        loan.setUnderwritingDecision(
                request.underwritingDecision() == null ? UnderwritingDecision.PENDING : request.underwritingDecision());
        return loan;
    }

    public static LoanResponse toResponse(Loan loan) {
        if (loan == null) {
            return null;
        }
        return new LoanResponse(loan.getId(), loan.getLoanExternalId(), loan.getInterestRate(),
                loan.getTermMonths(), loan.getUnderwritingDecision());
    }
}
