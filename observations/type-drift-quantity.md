# Type Drift Test: Invalid Quantity Values

## Test scenario

This test evaluated how the Rhombus pipeline handles type drift within an existing column while the dataset schema remains unchanged.

The baseline dataset contains 12,575 rows and 11 columns.

For this test, the first 100 non-empty values in the `Quantity` column were replaced with:

`INVALID_QUANTITY`

The drifted dataset was saved as:

`datasets/drift_quantity_type.csv`

The dataset retained:

- 12,575 rows
- 11 columns
- All original column names
- The original `Quantity` column

The drifted file was uploaded to S3 using the existing object key:

`baseline.csv`

This ensured that the Rhombus source configuration was unchanged.

## Expected behaviour

The original AI Builder cleaning requirements specified that:

- `Price Per Unit`, `Quantity`, and `Total Spent` must be numeric.
- Invalid numeric values should be treated as missing.
- Missing sales values must not be replaced with arbitrary numbers.
- The original 11-column schema should be preserved.

Therefore, I expected the pipeline to accept the unchanged schema and convert the 100 deliberately invalid `Quantity` values to missing values rather than failing, preserving them as strings, or inventing replacement quantities.

## Pre-run validation

Before upload, the drift dataset was independently checked.

Results:

- Rows: 12,575
- Columns: 11
- `INVALID_QUANTITY` values: 100
- `Price Per Unit` present: Yes
- `Category` present: Yes

This confirmed that the test represented value/type drift rather than schema drift.

## Scheduled execution behaviour

A scheduled execution was configured while the drifted dataset was present in S3.

However, after the scheduled time passed:

- The Executions view showed no results.
- The Logs panel showed no logs.
- Success count: 0
- Warning count: 0
- Error count: 0

Because there was no evidence that the scheduled execution actually started, this attempt was not treated as evidence of pipeline behaviour for the type drift itself.

This provides additional evidence of inconsistent schedule triggering or execution visibility.

## Controlled manual execution

To separate pipeline behaviour from scheduler behaviour, the same pipeline was manually executed without changing the source data or transformations.

The manual execution completed successfully.

Observed results included:

- `Pipeline execution started`
- `Pipeline execution completed successfully`
- `Pipeline completed successfully`
- 8 transformations applied
- 0 warnings
- 0 errors

The schema-validation step accepted the dataset because all 11 required columns remained present.

## GCS output

The successful manual execution created a new GCS object at approximately:

`12:11:39`

This was the third output object in the destination bucket.

The existence of the new object confirmed that the type-drift dataset passed through the complete pipeline and reached the configured GCS destination.

## Independent output validation

The newly generated GCS CSV was downloaded and independently inspected.

Results:

- Output rows: 12,575
- Output columns: 11
- Original schema preserved: Yes
- `INVALID_QUANTITY` remaining: 0
- Blank `Quantity` values: 704
- Non-empty non-numeric `Quantity` values: 0

The original baseline contained 604 missing `Quantity` values.

The drift test deliberately replaced 100 previously non-empty `Quantity` values with `INVALID_QUANTITY`.

Therefore:

`604 original missing + 100 deliberately invalid = 704 missing`

The output contained exactly 704 blank `Quantity` values.

This strongly indicates that all 100 deliberately invalid values were converted to missing values as required.

No non-empty non-numeric `Quantity` values remained.

## Result

**Schema preserved: YES**

**Schema validation passed: YES**

**100 invalid numeric values detected/cleaned: YES**

**Invalid strings remaining in output: NO**

**Arbitrary replacement quantities introduced: NO evidence observed**

**Manual pipeline execution successful: YES**

**GCS output produced: YES**

**Scheduled execution observed: NO**

The pipeline handled this controlled numeric type drift correctly.

Rather than rejecting the entire dataset, the cleaning transformation converted invalid `Quantity` values to missing values while preserving the dataset schema and row count.

## Key QA finding

Rhombus demonstrated useful resilience to value-level type drift.

The AI-generated numeric-cleaning transformation behaved consistently with the requested cleaning rules: invalid numeric values were treated as missing rather than preserved as invalid strings or replaced with fabricated quantities.

Independent validation was important because a successful pipeline status alone would not prove that the corrupted values had actually been cleaned correctly.

The test also exposed a separate scheduling concern. The scheduled attempt produced no visible execution or logs, while a manual execution of the same pipeline and same S3 input completed successfully and generated GCS output.

This suggests that pipeline correctness and scheduler reliability should be evaluated separately.

## Chatbot usage

No chatbot remediation was required for the type drift itself because the pipeline successfully handled the invalid numeric values.

This contrasts with the schema-drift tests, where chatbot diagnosis and remediation were required.

## Evidence

Evidence captured during this test includes:

- Creation and validation of `datasets/drift_quantity_type.csv`
- Confirmation of exactly 100 `INVALID_QUANTITY` values
- Scheduled execution showing no execution/log result
- Successful manual execution logs
- New GCS output created at approximately 12:11:39
- Independent validation of the downloaded GCS output
- Confirmation that `INVALID_QUANTITY` was reduced from 100 to 0
- Confirmation that blank `Quantity` values increased from 604 to 704
- Confirmation that no non-empty non-numeric `Quantity` values remained