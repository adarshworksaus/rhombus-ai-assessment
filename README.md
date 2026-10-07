# Rhombus AI QA & Automation Assessment

This repository contains my QA and automation assessment of a scheduled ETL pipeline built in Rhombus AI.

The pipeline ingests a deliberately messy retail sales CSV from Amazon S3, cleans and validates the data using Rhombus AI Builder transformations, and exports the processed result to Google Cloud Storage (GCS).

The assessment focuses on functional behaviour, schema drift, type drift, semantic drift, scheduled execution, data quality, determinism, UI automation, and direct backend API testing.

---

## Pipeline Overview

### Source
- Amazon S3
- Input file: `baseline.csv`
- Dataset contains 12,575 rows and 11 columns
- Dataset intentionally contains missing values and inconsistent data requiring cleaning

### Transformations

The final pipeline follows this sequence:

```text
baseline_raw
    ↓
schema_validated
    ↓
deduped
    ↓
drop_missing_ids
    ↓
trimmed
    ↓
standardized_text
    ↓
numeric_enforced
    ↓
date_standardized
    ↓
boolean_standardized
    ↓
result
```

The transformation logic was created through Rhombus AI Builder.

The pipeline:

- validates the expected input schema
- removes duplicate rows
- removes rows without required identifiers
- trims whitespace
- standardises text fields
- converts numeric columns
- standardises dates
- standardises boolean values
- avoids fabricating missing sales values
- preserves the expected output schema

### Destination
- Google Cloud Storage
- CSV output
- Output filename: `baseline_cleaned`

---

## Repository Structure

```text
.
├── api-tests/
│   └── pipeline-api.spec.ts
│
├── data-validation/
│   └── validate_pipeline.py
│
├── datasets/
│   ├── baseline.csv
│   ├── drift_add_currency.csv
│   ├── drift_ambiguous_dates.csv
│   ├── drift_currency_units.csv
│   ├── drift_dates_dayfirst.csv
│   ├── drift_drop_category.csv
│   ├── drift_quantity_type.csv
│   └── drift_rename_price_column.csv
│
├── observations/
│   ├── evidence/
│   ├── scheduled-run-output-mismatch.md
│   ├── schema-drift-added-column.md
│   ├── schema-drift-drop-column.md
│   ├── schema-drift-renamed-column.md
│   ├── semantic-drift-ambiguous-dates.md
│   ├── semantic-drift-currency-units.md
│   └── type-drift-quantity.md
│
├── ui-tests/
│   └── tests/
│       └── pipeline.spec.ts
│
├── .env.example
├── .gitignore
└── README.md
```

---

## Test Dataset

The baseline dataset is a dirty retail sales dataset containing fields including:

- Transaction ID
- Customer ID
- Category
- Item
- Price Per Unit
- Quantity
- Total Spent
- Payment Method
- Location
- Transaction Date
- Discount Applied

The baseline contains 12,575 rows.

Missing values were intentionally retained in appropriate fields so the pipeline could be tested against realistic dirty data.

---

# Drift Testing

Multiple modified versions of the baseline dataset were created to test how the pipeline behaves when the upstream data contract changes.

| Drift case | Change introduced | Pipeline stopped? | Chatbot fix worked? | Severity | Observation |
|---|---|---|---|---|---|
| Dropped column | Removed `Category` | Initially no; yes after schema validation | Yes, after additional manual corrections | High | [Details](observations/schema-drift-drop-column.md) |
| Renamed column | `Price Per Unit` → `Unit Price` | Yes, after schema validation | Not independently verified | High | [Details](observations/schema-drift-renamed-column.md) |
| Added column | Added `Currency` | Initially no; yes after schema validation | Yes, after exact-schema remediation | High | [Details](observations/schema-drift-added-column.md) |
| Quantity type drift | Replaced 100 quantities with `INVALID_QUANTITY` | No; invalid values became missing | Not required | Medium | [Details](observations/type-drift-quantity.md) |
| Combined schema drift | Dropped `Category`, renamed `Price Per Unit`, added `Currency`, and injected 100 invalid `Quantity` values | Yes; stopped at `schema_validated` | Yes; chatbot fix was independently verified, but compile side effects required recovery | High | [Details](observations/schema-drift-combined.md) |
| Monetary semantic drift | Multiplied monetary values by 100 | No; pipeline completed | No automatic fix; chatbot identified missing scale validation | Critical | [Details](observations/semantic-drift-currency-units.md) |
| Ambiguous MM/DD dates | Introduced 500 ambiguous dates | No; dates retained intended meaning | Not required | Medium | [Details](observations/semantic-drift-ambiguous-dates.md) |
| Day-first DD/MM dates | Reinterpreted 500 ambiguous dates | No; 500 dates changed meaning | No verified fix; explicit date format recommended | Critical | [Details](observations/semantic-drift-dayfirst-dates.md) |

Detailed observations are available in the `/observations` directory.

---

# Data Validation

The validation script is located at:

```text
data-validation/validate_pipeline.py
```

It compares the processed GCS output against the source/reference data.

Recorded results for the baseline and drift scenarios are available in [data-validation/results.md](data-validation/results.md).

The validator checks:

- exact schema
- duplicate rows
- missing required identifiers
- leading/trailing whitespace
- numeric conversion
- missing-value handling
- ISO date formatting
- boolean standardisation
- output row count
- deterministic output
- date semantics
- monetary semantics

## Example

```bash
python3 data-validation/validate_pipeline.py \
  --input datasets/baseline.csv \
  --output /path/to/baseline_cleaned.csv \
  --reference datasets/baseline.csv
```

A second output can also be supplied to test determinism:

```bash
python3 data-validation/validate_pipeline.py \
  --input datasets/baseline.csv \
  --output /path/to/first_output.csv \
  --compare-output /path/to/second_output.csv \
  --reference datasets/baseline.csv
```

The clean pipeline produced identical canonical hashes across repeated executions, demonstrating deterministic output for the tested baseline.

---

# UI Automation

UI tests are implemented with Playwright.

Location:

```text
ui-tests/tests/pipeline.spec.ts
```

The tests connect to an authenticated Chrome session and verify the Rhombus workflow UI and pipeline execution.

The tests verify:

- the correct Rhombus workflow is open
- the configured input-to-output transformation graph is present and connected
- the AI-generated cleaning stages are present in the workflow
- AI Builder contains pipeline-specific context, including the configured GCS output
- the workflow has an active daily schedule
- the schedule configuration is loaded and enabled
- the pipeline can be started from the UI
- the UI enters a real running state and returns to idle after execution completes

The execution test waits for actual UI state changes rather than using fixed sleeps.

The workflow uses Amazon S3 as its source and Google Cloud Storage as its destination, as documented in the Pipeline Overview. Rhombus does not expose the underlying S3/GCS connection names as stable visible text on the workflow canvas or Workspace, so the UI suite does not make a brittle text-based assertion for those connection labels. Instead, it verifies the configured input-to-output graph, AI Builder pipeline context, schedule state, and real execution behaviour.

## Running UI Tests

Install dependencies:

```bash
cd ui-tests
npm install
```

Start Chrome with remote debugging:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/playwright-rhombus-profile"
```

Log into Rhombus AI in that Chrome window and open the workflow.

Then run:

```bash
npx playwright test
```

Current result:

```text
4 passed
```

Authentication is intentionally not stored in the repository.

---

# API Testing

Direct backend API tests are implemented with Playwright.

Location:

```text
api-tests/pipeline-api.spec.ts
```

The API endpoints used by the tests were identified from the actual network requests made by the Rhombus frontend rather than guessed.

Authentication headers are captured dynamically from the authenticated browser session and kept only in memory.

No authentication token is committed to this repository.

The tests include:

### Positive Test

Retrieves the workflow node configuration from the Rhombus backend and verifies a successful response.

### Negative Test

Requests workflow nodes using an invalid workflow ID and verifies that the backend rejects the request with a 4xx response.

## Running API Tests

```bash
cd api-tests
npm install
npx playwright test pipeline-api.spec.ts
```

Current result:

```text
2 passed
```

---

# Key Findings

## 1. Structural schema drift required explicit validation

Early testing showed that structural changes could move further through the pipeline than expected.

For example, adding a new `Currency` column initially allowed the column to propagate through the pipeline and into the exported output.

An explicit exact-schema validation stage was therefore added near the beginning of the pipeline.

After remediation, missing, renamed, and unexpected columns were rejected before downstream transformations.

---

## 2. Structurally valid data can still be semantically wrong

The most significant issue found was that successful type and schema validation does not guarantee that the data still has the correct meaning.

When monetary values were multiplied by 100, the pipeline continued successfully because the values were still valid numeric data.

The validation script detected 23,937 monetary field changes matching the 100× scale change.

No pipeline warning identified the semantic unit change.

This demonstrates the importance of validating business meaning in addition to schema and data type.

---

## 3. Ambiguous date parsing can silently corrupt data

A date drift test introduced 500 ambiguous dates.

When the source used day-first `DD/MM` values, the transformation logic parsed the dates without an explicit source format.

All 500 tested ambiguous dates were silently interpreted with the wrong month/day meaning.

The pipeline still completed successfully.

This was detectable only when the output was compared against a trusted semantic reference.

Date parsing should therefore use an explicit expected source format rather than relying on automatic inference for ambiguous values.

---

# Additional Observations

## Pipeline status messaging

During drift testing, some executions produced inconsistent status information.

For example, an execution could display a generic successful pipeline completion message while a schema-validation stage reported a failure.

This makes it difficult for a user to determine whether the overall execution should be considered successful.

Top-level execution status should reflect downstream node failures consistently.

## Scheduled execution

Scheduled execution was also less observable than manual execution during testing.

Some scheduled runs produced limited visible execution information, while later control runs produced normal output.

Improved schedule history, timestamps, per-run status, and links to generated outputs would make scheduled pipelines easier to debug.

---

# Usability Feedback

Rhombus AI makes it quick to construct data transformations through natural-language instructions, and the visual pipeline makes the overall data flow easy to understand.

The main usability improvements I would suggest are around observability and failure handling.

### Clearer execution status

A pipeline should not show a generic success message if a node has failed. A single authoritative run status would make failures much easier to understand.

### Better schema-contract support

Schema expectations are important enough that they should be configurable as a first-class pipeline feature rather than relying entirely on generated transformation code.

Useful options would include:

- fail on missing columns
- fail on unexpected columns
- validate column types
- allow selected optional columns

### Safer date handling

When a date format is ambiguous, AI-generated transformations should either require an explicit format or warn the user instead of silently choosing an interpretation.

### Stronger semantic validation

Numeric type validation cannot detect changes such as dollars becoming cents.

Optional data-quality rules for expected ranges, units, distributions, or relationships between fields would help detect these problems.

### Better scheduled-run visibility

A dedicated execution history showing schedule trigger time, start/end time, node failures, output destination, and exported files would make scheduled ETL pipelines easier to operate.

---

# Security

Credentials, authentication tokens, cloud secrets, and browser sessions are not committed to this repository.

Runtime authentication used by the automated tests is captured from an already authenticated browser session and remains local.

Environment-specific configuration should be stored outside source control.

---


## QA Results Dashboard

A lightweight dashboard summarising the baseline pipeline, drift experiments,
automation coverage and key QA findings is included in:

`dashboard/index.html`

Open it locally in a browser to view the assessment results dashboard.

# Demo Video

Demo video: https://drive.google.com/file/d/1e5f6Wbs9CUnIMj58-s8x43SpLnyb10BG/view?usp=sharing


The demo covers:

1. baseline pipeline execution
2. S3 input and GCS output
3. schema and semantic drift behaviour
4. data validation
5. Playwright UI automation
6. direct API testing
7. key findings and recommended improvements

---

# Summary

The pipeline successfully cleans and exports the baseline retail dataset and produces deterministic output under the tested baseline conditions.

The assessment also demonstrates that ETL reliability requires more than successful execution.

Structural schema validation successfully catches missing, renamed, and unexpected columns after remediation, while the semantic drift experiments demonstrate that valid-looking data can still become incorrect without triggering pipeline errors.

The strongest opportunities for improvement are therefore:

- explicit schema contracts
- semantic data-quality checks
- deterministic date parsing
- consistent pipeline failure reporting
- stronger scheduled-run observability
