# Implementation Plan: TCO Calculation Validation

## Overview

Incremental implementation of bug fixes, dead code removal, validation improvements, and property-based tests for the TCO calculation engine. Tasks are ordered to make safe, non-breaking changes first (dead code removal, parameter cleanup), then add new logic (IOPS billing, validation bounds), then wire everything together with comprehensive property tests.

## Tasks

- [x] 1. Remove dead `project_costs()` function and update imports
  - [x] 1.1 Remove the `project_costs()` function from `packages/tco_engine/calculator.py`
    - Delete the entire `project_costs` function definition
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Update `tests/unit/test_calculator.py` to remove `project_costs` references
    - Remove `project_costs` from the import statement
    - Remove `test_project_costs_scales_recurring_costs` and `test_project_costs_does_not_scale_hardware` test functions
    - _Requirements: 1.1, 1.2_

- [x] 2. Remove `utilization_percentage` parameter from EC2 calculation
  - [x] 2.1 Remove `utilization_percentage` parameter from `calculate_ec2_costs` in `packages/tco_engine/aws_costs.py`
    - Remove the parameter from the function signature
    - Remove it from the docstring Args section
    - _Requirements: 3.1, 3.2_
  - [x] 2.2 Update `_calculate_aws_breakdown` in `packages/tco_engine/calculator.py` to stop passing `utilization_percentage`
    - Remove `utilization_percentage=config.utilization_percentage` from the `calculate_ec2_costs` call
    - _Requirements: 3.3_
  - [x] 2.3 Update `tests/unit/test_aws_costs.py` to remove `utilization_percentage` from all `calculate_ec2_costs` calls
    - Remove the `utilization_percentage` keyword argument from every test calling `calculate_ec2_costs`
    - _Requirements: 3.1_

- [x] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Add gp3 IOPS billing above free tier
  - [ ] 4.1 Add gp3 IOPS charging logic to `calculate_ebs_costs` in `packages/tco_engine/aws_costs.py`
    - When `storage_iops` is provided and volume type is "gp3", charge $0.005/IOPS for each IOPS above 3000
    - When IOPS ≤ 3000 or is None, no additional IOPS charge
    - Preserve existing io2 IOPS logic unchanged
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [ ] 4.2 Add unit tests for gp3 IOPS billing in `tests/unit/test_aws_costs.py`
    - Test gp3 with IOPS above 3000 charges correctly
    - Test gp3 with IOPS at or below 3000 has no IOPS charge
    - Test gp3 with IOPS=None has no IOPS charge
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 5. Fix S3 pricing key mismatch
  - [ ] 5.1 Normalize S3 pricing keys to lowercase in `packages/pricing_service/fetcher.py`
    - In `_fetch_s3_pricing`, convert all keys to lowercase before returning
    - In `_get_fallback_s3_price`, ensure fallback dict uses lowercase keys
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 6. Add upper bound validation for compute parameters
  - [ ] 6.1 Add upper bound checks to `validate_configuration` in `packages/tco_engine/validation.py`
    - cpu_cores must not exceed 512
    - memory_gb must not exceed 4096
    - instance_count must not exceed 1000
    - storage_capacity_gb must not exceed 1,000,000
    - storage_iops must not exceed 256,000
    - bandwidth_mbps must not exceed 100,000
    - monthly_data_transfer_gb must not exceed 5,000,000
    - Each violation produces a descriptive error message
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  - [ ] 6.2 Add unit tests for upper bound validation in `tests/unit/test_validation.py`
    - Test each parameter at max+1 produces an error
    - Test each parameter at max value passes validation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [ ] 7. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Create property-based test infrastructure and generators
  - [ ] 8.1 Create `tests/property/test_tco_properties.py` with Hypothesis strategies
    - Create `valid_configuration()` strategy generating Configuration with all fields in valid ranges (respecting upper bounds)
    - Create `valid_aws_pricing()` strategy generating AWSPricing with realistic rate ranges
    - Add necessary imports (hypothesis, hypothesis.strategies, Decimal, project modules)
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 9. Implement property-based tests for cost correctness
  - [ ]* 9.1 Write property test for gp3 IOPS billing correctness
    - **Property 1: gp3 IOPS billing correctness**
    - Verify charge equals `max(0, iops - 3000) * 0.005 * 12 * years` for gp3 volumes
    - **Validates: Requirements 2.1, 2.2**
  - [ ]* 9.2 Write property test for io2 IOPS billing
    - **Property 2: io2 IOPS billing charges all provisioned IOPS**
    - Verify charge equals `iops * iops_rate * 12 * years` for io2 volumes
    - **Validates: Requirements 2.4**
  - [ ]* 9.3 Write property test for EC2 linear scaling with instance count
    - **Property 3: EC2 cost scales linearly with instance count**
    - Verify doubling instance_count doubles EC2 cost
    - **Validates: Requirements 9.1**
  - [ ]* 9.4 Write property test for EBS base storage linear scaling
    - **Property 4: EBS base storage cost scales linearly with capacity**
    - Verify doubling storage_capacity_gb doubles EBS cost (no IOPS charges)
    - **Validates: Requirements 9.2**
  - [ ]* 9.5 Write property test for S3 linear scaling
    - **Property 5: S3 cost scales linearly with capacity**
    - Verify doubling storage_capacity_gb doubles S3 cost
    - **Validates: Requirements 9.3**
  - [ ]* 9.6 Write property test for S3 pricing lookup
    - **Property 6: S3 pricing lookup uses provided rate**
    - Verify `calculate_s3_costs` uses the "standard" key value, not the hardcoded default
    - **Validates: Requirements 4.1, 4.3**

- [ ] 10. Implement property-based tests for system-level invariants
  - [ ]* 10.1 Write property test for non-negative costs
    - **Property 7: All costs are non-negative**
    - Verify every line item and total from `calculate_tco` is ≥ 0
    - **Validates: Requirements 6.1, 6.2, 6.3**
  - [ ]* 10.2 Write property test for monotonic multi-year scaling
    - **Property 8: Monotonic multi-year scaling**
    - Verify `total(1yr) ≤ total(3yr) ≤ total(5yr)` for both on-prem and AWS
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
  - [ ]* 10.3 Write property test for total equals sum of components
    - **Property 9: Total equals sum of components**
    - Verify `CostBreakdown.total == sum(item.amount for item in items)` for all breakdowns
    - **Validates: Requirements 8.1, 8.2**

- [ ] 11. Implement property-based tests for validation boundaries
  - [ ]* 11.1 Write property test for validation rejects out-of-range inputs
    - **Property 10: Validation rejects all out-of-range inputs**
    - Verify `validate_configuration` raises `ValidationError` for values outside valid ranges
    - **Validates: Requirements 5.1–5.7, 10.1**
  - [ ]* 11.2 Write property test for validation accepts in-range inputs
    - **Property 11: Validation accepts all in-range inputs**
    - Verify `validate_configuration` does not raise for values within valid ranges
    - **Validates: Requirements 10.2**
  - [ ]* 11.3 Write property test for validation rejects invalid storage types
    - **Property 12: Validation rejects invalid storage types**
    - Verify any string not in {"SSD", "HDD", "NVME"} raises `ValidationError`
    - **Validates: Requirements 10.3**

- [ ] 12. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Tasks 1–2 are safe removals that simplify the codebase before adding new logic
- Task 4 (gp3 IOPS) and Task 5 (S3 key fix) are independent bug fixes
- Task 6 (upper bounds) is independent of the other fixes
- Property tests (Tasks 9–11) validate all preceding implementation work
- Checkpoints at Tasks 3, 7, and 12 ensure incremental correctness
