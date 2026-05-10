# Requirements Document

## Introduction

This spec covers improvements to the TCO (Total Cost of Ownership) calculation engine to fix identified bugs, remove dead code, tighten input validation, and add comprehensive property-based tests to ensure ongoing correctness. The TCO engine calculates and compares on-premises vs. AWS cloud costs across 1, 3, and 5-year projections.

## Glossary

- **TCO_Engine**: The calculation engine that orchestrates on-premises and AWS cost comparisons
- **Calculator**: The main orchestrator module (`calculator.py`) that combines cost components into breakdowns
- **AWS_Cost_Module**: The module (`aws_costs.py`) responsible for EC2, EBS, S3, and data transfer cost calculations
- **Validator**: The input validation module (`validation.py`) that checks configuration parameters
- **Pricing_Fetcher**: The pricing service module (`fetcher.py`) that retrieves and caches AWS pricing data
- **Configuration**: A dataclass holding compute, storage, network, and workload parameters for TCO calculation
- **CostBreakdown**: A dataclass containing itemized cost line items and a total
- **gp3**: AWS General Purpose SSD EBS volume type, includes 3000 IOPS free with charges above that threshold
- **io2**: AWS Provisioned IOPS SSD EBS volume type
- **Property-Based Test**: A test that verifies a general property holds for all valid inputs using randomized generation (Hypothesis library)

## Requirements

### Requirement 1: Remove Dead Code

**User Story:** As a developer, I want unused code removed from the calculator module, so that the codebase is easier to maintain and there is no risk of accidentally calling buggy dead code.

#### Acceptance Criteria

1. THE Calculator SHALL NOT contain the `project_costs()` function
2. WHEN the TCO_Engine is imported, THE Calculator SHALL expose only `calculate_tco`, `Configuration`, `AWSPricing`, `CostBreakdown`, and `CostLineItem` as public API

### Requirement 2: Charge IOPS Above gp3 Free Tier

**User Story:** As a user, I want gp3 IOPS costs above the 3000 free-tier threshold to be included in the AWS cost calculation, so that the TCO comparison is accurate for high-IOPS workloads.

#### Acceptance Criteria

1. WHEN `storage_type` is "SSD" and `storage_iops` exceeds 3000, THE AWS_Cost_Module SHALL charge the IOPS rate for each IOPS above 3000
2. WHEN `storage_type` is "SSD" and `storage_iops` is 3000 or less, THE AWS_Cost_Module SHALL NOT add any IOPS charges
3. WHEN `storage_type` is "SSD" and `storage_iops` is null, THE AWS_Cost_Module SHALL NOT add any IOPS charges
4. WHEN `storage_type` is "NVME" (io2), THE AWS_Cost_Module SHALL charge the IOPS rate for all provisioned IOPS (existing behavior preserved)

### Requirement 3: Remove Unused utilization_percentage Parameter from EC2 Calculation

**User Story:** As a developer, I want the EC2 cost function signature to accurately reflect its inputs, so that callers are not misled into thinking utilization affects EC2 pricing.

#### Acceptance Criteria

1. THE AWS_Cost_Module `calculate_ec2_costs` function SHALL NOT accept a `utilization_percentage` parameter
2. WHEN `calculate_ec2_costs` is called, THE AWS_Cost_Module SHALL calculate cost based only on instance type, instance count, operating hours, and years
3. THE Calculator SHALL pass only the required parameters when calling `calculate_ec2_costs`

### Requirement 4: Fix S3 Pricing Key Mismatch

**User Story:** As a developer, I want consistent casing for S3 pricing keys between the fetcher and cost calculator, so that pricing lookups succeed without relying on fallback defaults.

#### Acceptance Criteria

1. THE Pricing_Fetcher SHALL use lowercase keys ("standard", "intelligent_tiering", "standard_ia", "onezone_ia", "glacier") in the S3 pricing dictionary
2. THE AWS_Cost_Module SHALL look up S3 pricing using lowercase keys
3. WHEN the Pricing_Fetcher returns S3 pricing data, THE AWS_Cost_Module SHALL retrieve the correct rate without falling through to a hardcoded default

### Requirement 5: Add Upper Bound Validation for Compute Parameters

**User Story:** As a user, I want the system to reject unreasonably large configuration values, so that accidental or malicious inputs do not produce meaningless cost projections.

#### Acceptance Criteria

1. WHEN `cpu_cores` exceeds 512, THE Validator SHALL return an error indicating the maximum allowed value
2. WHEN `memory_gb` exceeds 4096, THE Validator SHALL return an error indicating the maximum allowed value
3. WHEN `instance_count` exceeds 1000, THE Validator SHALL return an error indicating the maximum allowed value
4. WHEN `storage_capacity_gb` exceeds 1000000 (1 PB), THE Validator SHALL return an error indicating the maximum allowed value
5. WHEN `storage_iops` exceeds 256000, THE Validator SHALL return an error indicating the maximum allowed value
6. WHEN `bandwidth_mbps` exceeds 100000, THE Validator SHALL return an error indicating the maximum allowed value
7. WHEN `monthly_data_transfer_gb` exceeds 5000000, THE Validator SHALL return an error indicating the maximum allowed value

### Requirement 6: Property-Based Tests for Cost Non-Negativity

**User Story:** As a developer, I want property-based tests that verify all cost calculations produce non-negative results for any valid input, so that the engine never reports negative costs.

#### Acceptance Criteria

1. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce non-negative totals for on-premises breakdowns
2. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce non-negative totals for AWS breakdowns
3. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce non-negative amounts for every individual cost line item

### Requirement 7: Property-Based Tests for Monotonic Multi-Year Scaling

**User Story:** As a developer, I want property-based tests that verify multi-year costs are monotonically non-decreasing, so that longer time horizons never produce lower costs than shorter ones.

#### Acceptance Criteria

1. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce 3-year on-premises costs greater than or equal to 1-year on-premises costs
2. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce 5-year on-premises costs greater than or equal to 3-year on-premises costs
3. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce 3-year AWS costs greater than or equal to 1-year AWS costs
4. FOR ALL valid Configuration inputs, THE TCO_Engine SHALL produce 5-year AWS costs greater than or equal to 3-year AWS costs

### Requirement 8: Property-Based Tests for Total Equals Sum of Components

**User Story:** As a developer, I want property-based tests that verify the reported total always equals the sum of individual line items, so that no costs are lost or double-counted.

#### Acceptance Criteria

1. FOR ALL valid Configuration inputs and all year periods, THE CostBreakdown total SHALL equal the sum of all line item amounts for on-premises calculations
2. FOR ALL valid Configuration inputs and all year periods, THE CostBreakdown total SHALL equal the sum of all line item amounts for AWS calculations

### Requirement 9: Property-Based Tests for Linear Scaling

**User Story:** As a developer, I want property-based tests that verify doubling instance count doubles EC2 cost and doubling storage doubles EBS/S3 cost, so that the engine scales linearly with resource quantities.

#### Acceptance Criteria

1. FOR ALL valid inputs, WHEN instance_count is doubled, THE AWS_Cost_Module `calculate_ec2_costs` SHALL return exactly double the original EC2 cost
2. FOR ALL valid inputs, WHEN storage_capacity_gb is doubled, THE AWS_Cost_Module `calculate_ebs_costs` SHALL return exactly double the original base storage cost (excluding IOPS)
3. FOR ALL valid inputs, WHEN storage_capacity_gb is doubled, THE AWS_Cost_Module `calculate_s3_costs` SHALL return exactly double the original S3 cost

### Requirement 10: Property-Based Tests for Validation Completeness

**User Story:** As a developer, I want property-based tests that verify the validator rejects all out-of-range inputs and accepts all in-range inputs, so that validation boundaries are correct and complete.

#### Acceptance Criteria

1. FOR ALL integers outside the valid range for each parameter, THE Validator SHALL raise a ValidationError
2. FOR ALL integers within the valid range for each parameter, THE Validator SHALL NOT raise a ValidationError
3. FOR ALL invalid storage_type strings, THE Validator SHALL raise a ValidationError
