# Schema Drift Test 1 — Dropped Column

## Scenario

The `Category` column was deliberately removed from the source CSV while keeping the S3 object name unchanged as `baseline.csv`.

The purpose of this test was to determine how Rhombus AI handles a missing column during an automatically scheduled ETL execution.

## Baseline Schema

The original dataset contained 11 columns:

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

## Drift Introduced

`Category` was removed.

The drifted dataset contained:

- 12,575 rows
- 10 columns

The modified dataset was saved locally as:

`datasets/drift_drop_category.csv`

For the test, the file was uploaded to S3 using the original object name:

`baseline.csv`

This ensured that the source path used by the existing Rhombus pipeline did not change.

## Expected Behaviour

Because the pipeline was originally built against an 11-column schema and includes transformations involving `Category`, I expected Rhombus to detect the missing column.

Possible acceptable behaviours included:

- failing the affected transformation,
- stopping the pipeline,
- displaying a schema-drift warning,
- or otherwise notifying the user that the expected input schema had changed.

## Actual Behaviour

The scheduled pipeline triggered automatically after the modified source file was uploaded.

Rhombus logged:

`Pipeline execution started.`

followed by:

`Pipeline execution completed successfully.`

The run completed at approximately 1:38:40 AM.

No schema-drift warning or failure was visible in the execution logs.

The AI Builder continued to display the existing pipeline configuration, including its statement that the original 11-column schema was preserved.

## GCS Output Verification

After the scheduled run completed, the configured Google Cloud Storage destination was checked.

No new output object appeared.

The only object present was the earlier file:

`baseline_cleaned_1791294111982.csv`

created at approximately 12:41:53 AM.

Therefore, the scheduled run was reported by Rhombus as successful, but no corresponding new GCS output could be verified.

## Important Limitation

This result does not prove that Rhombus successfully processed the missing `Category` column.

A separate issue has already been observed where scheduled executions are reported as successful without producing a new object in the configured GCS destination.

Because of this existing scheduled-output issue, it may be masking the true schema-drift behaviour.

The strongest conclusion supported by this test is:

**Rhombus reported the scheduled execution as successful and displayed no visible schema-drift warning after the source `Category` column was removed, while no corresponding new GCS output could be verified.**

## Schedule Behaviour After Drift

The schedule remained configured and active after the run. No visible indication showed that the schedule had been disabled because of the source change.

## Evidence

Relevant screenshots are stored in:

`observations/evidence/`

Evidence includes:

- scheduled pipeline start and successful completion logs,
- the unchanged AI Builder pipeline,
- and the GCS bucket showing no new output object after the scheduled execution.

## Follow-up

Further drift tests will be performed independently.

The scheduled-output mismatch will be treated as a separate platform observation so that it is not incorrectly attributed to this specific schema change.