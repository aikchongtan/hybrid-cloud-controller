# Implementation Plan: Cosmetic UI Fixes

## Overview

This plan implements four CSS and HTML template fixes to address cosmetic UI issues identified during UAT. All changes are isolated to the presentation layer (templates and CSS) with no impact on business logic. The fixes improve visual consistency, readability, and WCAG AA accessibility compliance.

## Tasks

- [x] 1. Fix consistent card heights on home page
  - Modify `packages/web_ui/static/css/style.css` to add Flexbox rules for equal-height cards
  - Update `packages/web_ui/templates/index.html` to apply the `equal-height` class to the columns container
  - Verify all three feature cards (TCO Analysis, Provisioning, Monitoring) have equal heights
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 1.1 Write property test for equal card heights
  - **Property 1: Equal Card Heights**
  - **Validates: Requirements 1.1, 1.2, 1.3**
  - Generate random content variations for cards and verify all heights remain equal
  - _Requirements: 1.3_

- [x] 2. Fix instruction text contrast on configuration form
  - Update all instruction text elements in `packages/web_ui/templates/configuration.html` to use `has-text-grey-dark` class
  - Apply the class to all 10 instruction text elements (CPU cores, memory, instance count, storage type, storage capacity, IOPS, bandwidth, data transfer, utilization, operating hours)
  - Verify text color meets WCAG AA contrast ratio (4.5:1) on white background
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11_

- [ ]* 2.1 Write property test for instruction text contrast
  - **Property 2: Instruction Text Contrast Compliance**
  - **Validates: Requirements 2.1-2.10**
  - Verify all instruction text elements meet WCAG AA contrast requirements
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_

- [x] 3. Checkpoint - Verify home page and configuration form fixes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Increase question input field size on Q&A page
  - Modify the textarea styling in `packages/web_ui/templates/qa.html` to increase font size and padding
  - Change textarea rows from 1 to 2 for better visibility
  - Add `min-width: 100%` style to ensure full container width
  - Verify input field can display at least 100 characters comfortably
  - _Requirements: 3.1, 3.2, 3.3_

- [ ]* 4.1 Write property test for responsive input field behavior
  - **Property 4: Responsive Input Field Behavior**
  - **Validates: Requirements 3.3**
  - Test input field adapts appropriately across viewport widths (320px to 1920px)
  - _Requirements: 3.3_

- [x] 5. Fix cost detail text contrast on TCO results page
  - Update `packages/web_ui/templates/tco_results.html` to ensure explicit white background for `.cost-breakdown` section
  - Verify `.breakdown-category` and `.breakdown-amount` text colors meet WCAG AA contrast on white background
  - If breakdown items appear on dark backgrounds, add `has-text-white` class to ensure readability
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ]* 5.1 Write property test for cost detail contrast
  - **Property 3: Cost Detail Contrast Compliance**
  - **Validates: Requirements 4.1, 4.2**
  - Generate random cost data and verify all text meets WCAG AA contrast requirements
  - _Requirements: 4.1, 4.2_

- [x] 6. Final checkpoint - Verify all cosmetic fixes
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster implementation
- All changes are CSS/HTML only - no backend or business logic modifications
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across different inputs
- WCAG AA compliance requires 4.5:1 contrast ratio for normal text
- Bulma CSS framework classes are used where possible for consistency
