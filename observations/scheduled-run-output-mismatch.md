# Scheduled Execution and GCS Output Investigation

## Initial Observation

During early scheduled pipeline tests, Rhombus reported scheduled executions as successfully completed, but no corresponding new object appeared in the configured Google Cloud Storage bucket.

This behaviour was initially suspected to be a general scheduled-output issue.

However, later control testing showed that scheduled execution and GCS export work correctly when the original baseline schema is used.

## Initial Scheduled Runs

During schema-drift testing, scheduled executions produced log messages such as:

`Pipeline execution started.`

followed by:

`Pipeline execution completed successfully.`

No visible warnings or errors were reported.

Despite these success messages, the GCS bucket continued to contain only the output generated earlier at approximately 00:41:53.

No new GCS object corresponding to those drifted scheduled runs was observed.

## Control Test

To determine whether the scheduler or GCS output configuration was responsible, the original unmodified baseline dataset was restored to the S3 source.

The restored baseline contained:

- 12,575 rows
- 11 columns
- the original `Category` column
- the original `Price Per Unit` column
- no intentional schema drift

The Rhombus pipeline configuration was left unchanged.

The Data Output node was also verified to be connected to the final transformation and configured with:

- Google Cloud Storage destination: `rhombus-ai-assessment-output-a2026`
- Export format: CSV
- Custom filename: `baseline_cleaned`

The Rhombus UI states that data is exported automatically when the pipeline runs.

## Control Scheduled Execution

A new scheduled execution was performed using the restored baseline.

Rhombus logged:

`Pipeline execution started.`

at approximately 11:10:00 AM.

At approximately 11:10:21 AM, Rhombus logged successful completion and also reported that the pipeline transformations had been applied.

The run showed:

- 0 warnings
- 0 errors
- successful pipeline completion

## GCS Verification

After the control scheduled execution, the GCS bucket was refreshed.

A new output object was present with a creation timestamp of approximately 11:10:19 AM.

The bucket therefore contained both:

- the earlier output created at approximately 00:41:53
- a new output created at approximately 11:10:19

This confirms that scheduled execution can successfully run the pipeline and export data to the configured GCS destination when the original baseline input is present.

## Revised Finding

The earlier missing GCS outputs should not be classified as a general scheduler failure.

The control test demonstrates that:

**Original baseline → scheduled execution → transformations → GCS output**

works successfully.

In contrast, during the tested schema-drift scenarios, Rhombus reported successful scheduled execution without a corresponding new GCS output being observed.

This suggests that the missing outputs are associated with the drift scenarios or their processing rather than with scheduled execution in general.

Further drift testing is required to determine the exact behaviour.

## QA Significance

The important behaviour to investigate is the difference between the user-visible execution status and the observable downstream result during schema drift.

If a schema change prevents the pipeline from producing its configured output, the platform should ideally expose a clear failure, warning, or actionable diagnostic rather than only presenting a successful execution message.

The control test provides a known-good comparison for the remaining drift experiments.