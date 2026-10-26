package com.capstone.mortgage.service;

import com.capstone.mortgage.configuration.CorrelationIdHolder;
import com.capstone.mortgage.dto.MortgageRequest;
import com.capstone.mortgage.dto.MortgageResponse;
import com.capstone.mortgage.dto.PageResponse;
import com.capstone.mortgage.entity.Borrower;
import com.capstone.mortgage.entity.Loan;
import com.capstone.mortgage.entity.Mortgage;
import com.capstone.mortgage.entity.MortgageStatus;
import com.capstone.mortgage.entity.ServicingHistory;
import com.capstone.mortgage.exception.ConflictException;
import com.capstone.mortgage.exception.NotFoundException;
import com.capstone.mortgage.mapper.LoanMapper;
import com.capstone.mortgage.mapper.MortgageMapper;
import com.capstone.mortgage.repository.BorrowerRepository;
import com.capstone.mortgage.repository.LoanRepository;
import com.capstone.mortgage.repository.MortgageRepository;
import com.capstone.mortgage.repository.ServicingHistoryRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;

@Service
public class MortgageServiceImpl implements MortgageService {

    private static final Logger log = LoggerFactory.getLogger(MortgageServiceImpl.class);

    private final MortgageRepository mortgageRepository;
    private final BorrowerRepository borrowerRepository;
    private final LoanRepository loanRepository;
    private final ServicingHistoryRepository servicingHistoryRepository;

    public MortgageServiceImpl(MortgageRepository mortgageRepository, BorrowerRepository borrowerRepository,
                                LoanRepository loanRepository, ServicingHistoryRepository servicingHistoryRepository) {
        this.mortgageRepository = mortgageRepository;
        this.borrowerRepository = borrowerRepository;
        this.loanRepository = loanRepository;
        this.servicingHistoryRepository = servicingHistoryRepository;
    }

    @Override
    @Transactional
    public MortgageResponse create(MortgageRequest request) {
        if (mortgageRepository.existsByMortgageExternalId(request.mortgageExternalId())) {
            throw new ConflictException("MORTGAGE_ALREADY_EXISTS",
                    "Mortgage " + request.mortgageExternalId() + " already exists");
        }
        Borrower borrower = borrowerRepository.findByBorrowerExternalId(request.borrowerExternalId())
                .orElseThrow(() -> new NotFoundException("BORROWER_NOT_FOUND",
                        "Borrower " + request.borrowerExternalId() + " was not found"));

        Mortgage mortgage = new Mortgage();
        mortgage.setMortgageExternalId(request.mortgageExternalId());
        mortgage.setBorrower(borrower);
        mortgage.setStatus(MortgageStatus.PENDING);
        mortgage.setOriginalAmount(request.originalAmount());
        mortgage.setOutstandingBalance(request.outstandingBalance());
        mortgage.setOriginationDate(request.originationDate());
        Mortgage savedMortgage = mortgageRepository.save(mortgage);

        Loan savedLoan = null;
        if (request.loan() != null) {
            if (loanRepository.existsByLoanExternalId(request.loan().loanExternalId())) {
                throw new ConflictException("LOAN_ALREADY_EXISTS",
                        "Loan " + request.loan().loanExternalId() + " already exists");
            }
            Loan loan = LoanMapper.toEntity(request.loan(), savedMortgage);
            savedLoan = loanRepository.save(loan);
            savedMortgage.setStatus(loan.getUnderwritingDecision() == com.capstone.mortgage.entity.UnderwritingDecision.APPROVED
                    ? MortgageStatus.ACTIVE : MortgageStatus.PENDING);
        }

        ServicingHistory onboarded = new ServicingHistory();
        onboarded.setMortgage(savedMortgage);
        onboarded.setEventTime(OffsetDateTime.now());
        onboarded.setEventType("ONBOARDING_COMPLETE");
        onboarded.setDescription("Mortgage onboarded via mortgage-service");
        servicingHistoryRepository.save(onboarded);

        log.info("Mortgage created mortgageExternalId={} correlationId={}",
                savedMortgage.getMortgageExternalId(), CorrelationIdHolder.get());

        return MortgageMapper.toResponse(savedMortgage, savedLoan);
    }

    @Override
    @Transactional(readOnly = true)
    public MortgageResponse getByExternalId(String mortgageExternalId) {
        Mortgage mortgage = findMortgageOrThrow(mortgageExternalId);
        Loan loan = loanRepository.findByMortgage(mortgage).orElse(null);
        return MortgageMapper.toResponse(mortgage, loan);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<MortgageResponse> list(String borrowerExternalId, Pageable pageable) {
        Page<Mortgage> page;
        if (borrowerExternalId != null && !borrowerExternalId.isBlank()) {
            page = mortgageRepository.findByBorrower_BorrowerExternalId(borrowerExternalId, pageable);
        } else {
            page = mortgageRepository.findAll(pageable);
        }
        Page<MortgageResponse> mapped = page.map(m -> MortgageMapper.toResponse(m,
                loanRepository.findByMortgage(m).orElse(null)));
        return com.capstone.mortgage.dto.PageResponse.from(mapped);
    }

    Mortgage findMortgageOrThrow(String mortgageExternalId) {
        return mortgageRepository.findByMortgageExternalId(mortgageExternalId)
                .orElseThrow(() -> new NotFoundException("MORTGAGE_NOT_FOUND",
                        "Mortgage " + mortgageExternalId + " was not found"));
    }
}
