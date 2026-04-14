# Design Document: Cosmetic UI Fixes

## Overview

This design specifies CSS and HTML template modifications to fix four cosmetic UI issues identified during User Acceptance Testing. The fixes address visual consistency, readability, and WCAG AA accessibility compliance across the web UI. All changes are isolated to presentation layer (CSS/HTML templates) with no impact on business logic or backend functionality.

The web UI uses the Bulma CSS framework (version 0.9.x) and Flask with Jinja2 templates. Changes leverage Bulma's utility classes where possible to maintain framework consistency and reduce custom CSS.

## Architecture

### Component Overview

The fixes target four distinct UI components:

1. **Home Page Cards** (`templates/index.html`) - Three feature cards with inconsistent heights
2. **Configuration Form** (`templates/configuration.html`) - Instruction text with insufficient contrast
3. **Q&A Page** (`templates/qa.html`) - Question input field with inadequate width
4. **TCO Results Page** (`templates/tco_results.html`) - Cost breakdown text with low contrast

### Technology Stack

- **Frontend Framework**: Bulma CSS 0.9.x
- **Template Engine**: Jinja2 (Flask)
- **Custom Styles**: `static/css/style.css`
- **Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)

### Design Principles

- Use Bulma utility classes for consistency
- Minimize custom CSS additions
- Maintain responsive behavior across screen sizes
- Ensure WCAG AA compliance (4.5:1 contrast ratio for normal text)
- Preserve all existing functionality

## Components and Interfaces

### Fix 1: Consistent Card Heights on Home Page

**File**: `templates/index.html`

**Current State**:
- Three cards in a `.columns` container
- Cards have variable heights based on content length
- TCO Analysis card is taller than Provisioning and Monitoring cards

**Solution**:
Add CSS to ensure equal card heights using Flexbox:

```css
/* In static/css/style.css */
.columns.equal-height {
    display: flex;
}

.columns.equal-height .column {
    display: flex;
}

.columns.equal-height .card {
    display: flex;
    flex-direction: column;
    width: 100%;
}

.columns.equal-height .card-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.columns.equal-height .card-content .content {
    flex: 1;
}
```

**Template Modification**:
Change `<div class="columns mt-5">` to `<div class="columns mt-5 equal-height">` in `index.html`.

**Rationale**: Flexbox ensures all cards stretch to match the tallest card's height while maintaining content flow.

### Fix 2: Accessible Instruction Text on Configuration Form

**File**: `templates/configuration.html`

**Current State**:
- Instruction text uses default Bulma `.help` class
- Default color is `#7a7a7a` (light grey) on white background
- Contrast ratio: ~4.0:1 (fails WCAG AA 4.5:1 requirement)

**Solution**:
Replace `.help` class with `.help has-text-grey-dark` for all instruction text elements.

**Bulma Color Reference**:
- `has-text-grey-dark`: `#4a4a4a` (provides 8.6:1 contrast on white)
- Meets WCAG AA standard (4.5:1) and AAA standard (7:1)

**Template Modifications**:
Change all instances of:
```html
<p class="help">Instruction text here</p>
```

To:
```html
<p class="help has-text-grey-dark">Instruction text here</p>
```

**Affected Elements** (10 total):
1. CPU cores: "Number of CPU cores (positive integer)"
2. Memory: "Memory size in gigabytes (positive number)"
3. Instance count: "Number of instances (positive integer)"
4. Storage type: "Type of storage (SSD, HDD, or NVMe)"
5. Storage capacity: "Storage capacity in gigabytes (positive number)"
6. Storage IOPS: "Input/Output operations per second (optional)"
7. Bandwidth: "Network bandwidth in megabits per second (positive number)"
8. Data transfer: "Monthly data transfer in gigabytes (positive number)"
9. Utilization: "Expected resource utilization (0-100%)"
10. Operating hours: "Hours of operation per month (0-744)"

**Rationale**: Using Bulma's built-in color utility maintains framework consistency and ensures accessibility compliance.

### Fix 3: Adequate Question Input Field Size on Q&A Page

**File**: `templates/qa.html`

**Current State**:
- Question input is a `<textarea>` with default width
- Appears small relative to page layout
- Difficult to review longer questions

**Solution**:
Modify the textarea styling in the existing `<style>` block:

```css
/* In qa.html <style> block, modify .chat-input-wrapper textarea */
.chat-input-wrapper textarea {
    flex: 1;
    resize: none;
    min-height: 50px;
    max-height: 150px;
    font-size: 1rem;        /* Add this */
    padding: 0.75rem 1rem;  /* Add this */
}
```

**Additional Modification**:
Update the textarea element to set a minimum width:

```html
<textarea 
    class="textarea" 
    id="questionInput" 
    placeholder="Ask a question about your TCO analysis..."
    rows="2"
    style="min-width: 100%;"
    required></textarea>
```

Change `rows="1"` to `rows="2"` to show more text by default.

**Rationale**: Increased font size, padding, and default rows make the input field more prominent and easier to use. The field already uses `flex: 1` to fill available horizontal space.

### Fix 4: Readable Cost Details on TCO Results Page

**File**: `templates/tco_results.html`

**Current State**:
- Cost breakdown items use `.breakdown-category` and `.breakdown-amount` classes
- `.breakdown-category` color: `#363636` (dark grey)
- `.breakdown-amount` color: `#3273dc` (blue)
- Cards have gradient backgrounds (dark purple/pink to black)
- Text contrast is insufficient on dark backgrounds

**Solution**:
The cost breakdown is inside `.cost-breakdown` which has a white background (inside `.comparison-card`). However, the issue description mentions "grey text on black background", suggesting the breakdown items may appear on the gradient header.

**Investigation**: Looking at the template structure:
- `.cost-header` has gradient background
- `.cost-breakdown` has default (white) background
- Breakdown items are inside `.cost-breakdown`

**Actual Issue**: The breakdown items are correctly placed in white background area. The issue may be with the visual perception or a different element.

**Solution**: Add explicit background color and ensure text colors meet WCAG AA:

```css
/* In tco_results.html <style> block, modify .cost-breakdown */
.cost-breakdown {
    padding: 1.5rem;
    background-color: #ffffff;  /* Explicit white background */
}

.breakdown-category {
    font-weight: 500;
    color: #363636;  /* Already good contrast on white */
}

.breakdown-amount {
    font-weight: 600;
    color: #3273dc;  /* Already good contrast on white */
}
```

**Alternative Solution** (if items are on dark background):
If breakdown items appear on dark backgrounds, use Bulma's light text classes:

```html
<div class="breakdown-item">
    <span class="breakdown-category has-text-white">{{ item.description }}</span>
    <span class="breakdown-amount has-text-white">$\{{ "{:,.2f}".format(item.amount|float) }}</span>
</div>
```

**Rationale**: Explicit white background ensures cost details remain readable. If items appear on dark backgrounds, white text provides maximum contrast (21:1 ratio).

## Data Models

No data model changes required. All fixes are presentation-layer only.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptance Criteria Testing Prework

#### Requirement 1: Consistent Card Heights on Home Page

1.1 THE Web_UI SHALL display the TCO Analysis card with the same height as the Provisioning card on the home page
  Thoughts: This is a visual property that can be tested by measuring rendered element heights in the DOM. We can verify that all three cards have equal computed heights.
  Testable: yes - example

1.2 THE Web_UI SHALL display the TCO Analysis card with the same height as the Monitoring card on the home page
  Thoughts: Same as 1.1, this is redundant if we test that all three cards have equal heights.
  Testable: yes - example (redundant with 1.1)

1.3 THE Web_UI SHALL maintain equal card heights across all three feature cards regardless of text content length
  Thoughts: This is a property that should hold for any content. We can test by varying content length and verifying heights remain equal.
  Testable: yes - property

1.4 THE Web_UI SHALL preserve all existing card functionality and content
  Thoughts: This is about ensuring no regression. We can verify that all links, text, and interactive elements remain functional.
  Testable: yes - example

#### Requirement 2: Accessible Instruction Text on Configuration Form

2.1-2.10 THE Web_UI SHALL display instruction text for [field] with WCAG_AA compliant contrast ratio
  Thoughts: All 10 criteria test the same property - that instruction text meets 4.5:1 contrast ratio. This is a single property applied to multiple elements.
  Testable: yes - property

2.11 THE Web_UI SHALL use Bulma CSS classes for text color styling to maintain framework consistency
  Thoughts: This is a code quality check, not a functional requirement. We can verify by inspecting the HTML for Bulma class usage.
  Testable: yes - example

#### Requirement 3: Adequate Question Input Field Size on Q&A Page

3.1 THE Web_UI SHALL display the question input field with sufficient width to show at least 100 characters
  Thoughts: This is testable by measuring the input field width and calculating character capacity based on font metrics.
  Testable: yes - example

3.2 THE Web_UI SHALL maintain the question input field's existing functionality for text entry and submission
  Thoughts: This is a regression test to ensure functionality is preserved.
  Testable: yes - example

3.3 THE Web_UI SHALL preserve the question input field's responsive behavior across different screen sizes
  Thoughts: This tests that the field adapts to different viewport widths. We can test at standard breakpoints (mobile, tablet, desktop).
  Testable: yes - property

#### Requirement 4: Readable Cost Details on TCO Results Page

4.1 THE Web_UI SHALL display Cost_Line_Item text under the On-Premises card with WCAG_AA compliant contrast ratio against the card background
  Thoughts: This tests contrast ratio for specific elements. Can be verified by measuring computed colors and calculating contrast.
  Testable: yes - example

4.2 THE Web_UI SHALL display Cost_Line_Item text under the AWS Cloud card with WCAG_AA compliant contrast ratio against the card background
  Thoughts: Same as 4.1 but for AWS card. These can be combined into one property.
  Testable: yes - example

4.3 THE Web_UI SHALL use Bulma CSS classes for text color styling to maintain framework consistency
  Thoughts: Code quality check, same as 2.11.
  Testable: yes - example

4.4 THE Web_UI SHALL preserve all existing cost calculation and display functionality
  Thoughts: Regression test to ensure no functional changes.
  Testable: yes - example

### Property Reflection

Reviewing the prework analysis:

**Redundancies identified**:
- Requirements 1.1 and 1.2 are redundant with 1.3 (all three test equal card heights)
- Requirements 2.1-2.10 all test the same property (WCAG AA contrast for instruction text)
- Requirements 4.1 and 4.2 test the same property (WCAG AA contrast for cost details)

**Consolidation**:
- Combine 1.1, 1.2, 1.3 into one property about equal card heights
- Combine 2.1-2.10 into one property about instruction text contrast
- Combine 4.1 and 4.2 into one property about cost detail contrast
- Keep regression tests (1.4, 3.2, 4.4) as examples
- Keep code quality checks (2.11, 4.3) as examples
- Keep specific measurements (3.1) as examples
- Keep responsive behavior (3.3) as a property

### Property 1: Equal Card Heights

*For any* content variations in the three feature cards on the home page, all cards should have equal computed heights when rendered.

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Instruction Text Contrast Compliance

*For any* instruction text element (`.help` class) on the configuration form, the text color should have a contrast ratio of at least 4.5:1 against the background color.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**

### Property 3: Cost Detail Contrast Compliance

*For any* cost breakdown item on the TCO results page, the text color should have a contrast ratio of at least 4.5:1 against the background color.

**Validates: Requirements 4.1, 4.2**

### Property 4: Responsive Input Field Behavior

*For any* viewport width (mobile, tablet, desktop breakpoints), the question input field should maintain usability by adapting its width appropriately to the container.

**Validates: Requirements 3.3**

## Error Handling

No error handling changes required. All fixes are CSS/HTML presentation changes that cannot fail at runtime. If CSS fails to load, the page falls back to default Bulma styles, maintaining basic functionality.

### Potential Issues

1. **Browser Compatibility**: Flexbox is well-supported in modern browsers. No fallback needed for target browsers.
2. **CSS Specificity**: New CSS rules use class selectors with appropriate specificity to override defaults without `!important`.
3. **Responsive Breakpoints**: Bulma's responsive utilities handle mobile/tablet/desktop layouts automatically.

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific examples (e.g., home page cards have equal heights, specific instruction text meets contrast requirements)
- **Property tests**: Verify universal properties (e.g., all instruction text elements meet WCAG AA, responsive behavior works across viewport ranges)

### Unit Testing

**Framework**: Selenium WebDriver with Python (pytest)

**Test Cases**:

1. **Home Page Card Heights**
   - Load home page
   - Measure computed heights of all three cards
   - Assert all heights are equal (within 1px tolerance)
   - Verify card content and links are intact

2. **Configuration Form Instruction Text**
   - Load configuration page
   - For each instruction text element:
     - Get computed color values (text and background)
     - Calculate contrast ratio
     - Assert ratio >= 4.5:1
   - Verify all instruction text uses `has-text-grey-dark` class

3. **Q&A Input Field Size**
   - Load Q&A page
   - Measure input field width
   - Calculate character capacity (width / average character width)
   - Assert capacity >= 100 characters
   - Verify input functionality (type text, submit)

4. **TCO Results Cost Details**
   - Load TCO results page
   - For each cost breakdown item:
     - Get computed color values (text and background)
     - Calculate contrast ratio
     - Assert ratio >= 4.5:1
   - Verify cost calculations are unchanged

5. **Responsive Behavior**
   - Test at breakpoints: 320px (mobile), 768px (tablet), 1024px (desktop)
   - Verify layouts adapt appropriately
   - Verify no horizontal scrolling
   - Verify text remains readable

### Property-Based Testing

**Framework**: Hypothesis with Selenium WebDriver

**Configuration**: Minimum 100 iterations per property test

**Property Tests**:

1. **Property Test: Equal Card Heights**
   - **Tag**: Feature: cosmetic-ui-fixes, Property 1: For any content variations in the three feature cards on the home page, all cards should have equal computed heights when rendered.
   - **Strategy**: Generate random content lengths for each card, render page, verify all heights are equal
   - **Generators**: 
     - Card content: strings of varying lengths (10-500 characters)
     - Button text: strings of varying lengths (5-50 characters)
   - **Assertion**: `height(card1) == height(card2) == height(card3)`

2. **Property Test: Instruction Text Contrast**
   - **Tag**: Feature: cosmetic-ui-fixes, Property 2: For any instruction text element on the configuration form, the text color should have a contrast ratio of at least 4.5:1 against the background color.
   - **Strategy**: For all instruction text elements, verify contrast ratio
   - **Generators**: Not needed (tests existing elements)
   - **Assertion**: `contrast_ratio(text_color, bg_color) >= 4.5`

3. **Property Test: Cost Detail Contrast**
   - **Tag**: Feature: cosmetic-ui-fixes, Property 3: For any cost breakdown item on the TCO results page, the text color should have a contrast ratio of at least 4.5:1 against the background color.
   - **Strategy**: Generate random cost data, render results, verify all text meets contrast requirements
   - **Generators**:
     - Cost amounts: positive floats (0.01 to 1000000.00)
     - Cost descriptions: strings (10-100 characters)
   - **Assertion**: `contrast_ratio(text_color, bg_color) >= 4.5`

4. **Property Test: Responsive Input Field**
   - **Tag**: Feature: cosmetic-ui-fixes, Property 4: For any viewport width, the question input field should maintain usability by adapting its width appropriately to the container.
   - **Strategy**: Generate random viewport widths, verify input field adapts
   - **Generators**: Viewport widths (320px to 1920px)
   - **Assertion**: `input_width <= container_width AND input_width >= min_usable_width`

### Test Utilities

**Contrast Ratio Calculator**:
```python
def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """
    Calculate WCAG contrast ratio between two colors.
    
    Args:
        color1: RGB color string (e.g., "rgb(74, 74, 74)")
        color2: RGB color string (e.g., "rgb(255, 255, 255)")
    
    Returns:
        Contrast ratio (1.0 to 21.0)
    """
    # Parse RGB values
    # Calculate relative luminance
    # Return (L1 + 0.05) / (L2 + 0.05) where L1 > L2
```

**Element Height Comparator**:
```python
def assert_equal_heights(elements: list, tolerance: int = 1) -> None:
    """
    Assert all elements have equal computed heights.
    
    Args:
        elements: List of WebElement objects
        tolerance: Allowed height difference in pixels
    """
    heights = [el.size['height'] for el in elements]
    assert max(heights) - min(heights) <= tolerance
```

### Test Execution

- Run unit tests on every commit
- Run property tests nightly (due to longer execution time)
- Test on multiple browsers: Chrome, Firefox, Safari, Edge
- Test on multiple screen sizes: mobile (375px), tablet (768px), desktop (1920px)

### Success Criteria

- All unit tests pass
- All property tests pass (100 iterations each)
- No visual regressions detected
- WCAG AA compliance verified with automated tools (axe-core)
- Manual accessibility review confirms improvements
