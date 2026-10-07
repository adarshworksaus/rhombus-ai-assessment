# Schema Drift Test: Unexpected Added Column

## Test scenario

This test evaluated how the Rhombus pipeline handles an unexpected additional column while all original required columns remain present.

The baseline dataset contains:

- 12,575 rows
- 11 columns

For this drift case, a new column named `Currency` was added.

Every row was assigned:

`Currency = AUD`

The resulting dataset contained:

- 12,575 rows
- 12 columns
- All original 11 columns unchanged
- One additional `Currency` column
- 12,575 `AUD` values

The drifted dataset was saved as:

`datasets/drift_add_currency.csv`

It was uploaded to S3 using the existing object key:

`baseline.csv`

The Rhombus source configuration was therefore unchanged.

## Expected behaviour

The `schema_validated` node had been introduced to enforce the original 11-column schema.

The intended contract was that the input should contain exactly these 11 columns:

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

Because the drifted dataset contained a 12th unexpected column, `Currency`, I expected strict schema validation to reject the input before downstream transformations or export.

## Initial execution result

The pipeline was manually executed with the 12-column drifted dataset present in S3.

The pipeline completed successfully.

Observed execution behaviour:

- Pipeline execution started
- Pipeline execution completed successfully
- Pipeline completed successfully
- 8 transformations applied
- 12,575 rows processed
- 0 warnings
- 0 errors

The `schema_validated` node did not reject the additional `Currency` column.

## Initial GCS result

A new GCS output object was created at approximately:

`12:16:45`

This confirmed that the unexpected schema was allowed through the complete pipeline and reached the configured destination.

## Independent output validation

The newly generated GCS CSV was downloaded and independently inspected.

Results:

- Output rows: 12,575
- Output columns: 12
- `Currency` present: Yes
- `Currency = AUD` rows: 12,575
- Blank Currency values: 0
- Unique Currency values: `['AUD']`

Therefore, the unexpected column was not only accepted by the validation node but also survived every downstream transformation and was exported to GCS unchanged.

## Chatbot diagnosis

The Rhombus chatbot was asked to inspect the current generated code without modifying the pipeline.

It reported that `schema_validated` used the following logic:

```python
required_columns = [
    'Transaction ID', 'Customer ID', 'Category', 'Item',
    'Price Per Unit', 'Quantity', 'Total Spent', 'Payment Method',
    'Location', 'Transaction Date', 'Discount Applied'
]

missing_columns = [
    col for col in required_columns
    if col not in input_df_1.columns
]

if missing_columns:
    raise ValueError(
        f"Schema validation failed: missing required column(s): {missing_columns}"
    )

output_df = input_df_1.copy()
```

This implementation checks only whether required columns are missing.

It does not check whether unexpected columns are present.

Conceptually, the generated validation checks:

`required columns ⊆ input columns`

rather than enforcing:

`required columns = input columns`

Because all 11 required columns were present in the drifted input, `missing_columns` was empty and validation succeeded.

The subsequent:

`output_df = input_df_1.copy()`

also copied the unexpected `Currency` column into the output.

The chatbot further explained that downstream transformations operate on selected named columns while preserving the rest of the DataFrame, allowing `Currency` to propagate unchanged to GCS.

## Root cause

The generated schema-validation implementation did not match the intended strict schema contract.

Although the node was intended to validate exactly the original 11-column schema, its generated implementation performed only a required-column presence check.

There was no logic to calculate or reject unexpected columns.

For example, strict validation additionally requires comparing the actual input columns against the expected columns and rejecting columns that exist only in the input.

This exposed a mismatch between the natural-language intent supplied to AI Builder and the code it generated.

## Initial result

**Original 11 required columns present: YES**

**Unexpected additional column present: YES**

**Strict schema validation triggered: NO**

**Pipeline completed successfully: YES**

**Warning generated: NO**

**Error generated: NO**

**Unexpected column reached GCS: YES**

**All 12,575 Currency values preserved: YES**

The initial implementation therefore enforced required-column presence but did not enforce exact schema equality.

## AI Builder remediation

After documenting the original behaviour, AI Builder was asked to apply a minimal fix to the existing `schema_validated` node.

The remediation request explicitly instructed AI Builder:

- Do not create a new node.
- Do not change pipeline connections.
- Do not modify `deduped`.
- Do not modify downstream transformations.
- Do not modify the S3 or GCS configuration.
- Detect both missing and unexpected columns.
- Preserve the original 11-column contract.

AI Builder reported that the live `schema_validated` code was updated to compare the expected and actual schemas in both directions.

### Missing-column validation

```python
expected_set = set(required_columns)
actual_set = set(input_df_1.columns)

missing_columns = sorted(expected_set - actual_set)

if missing_columns:
    raise ValueError(
        f"Schema validation failed: missing required column(s): {missing_columns}"
    )
```

This calculates:

`expected columns − actual columns`

and therefore identifies required columns that are absent from the input.

### Unexpected-column validation

```python
extra_columns = sorted(actual_set - expected_set)

if extra_columns:
    raise ValueError(
        f"Schema validation failed: unexpected column(s) not in contract: {extra_columns}"
    )
```

This calculates:

`actual columns − expected columns`

and therefore identifies columns that are present in the input but absent from the schema contract.

Together, the two checks enforce strict schema equality rather than only checking required-column presence.

## Pipeline wiring verification after remediation

Because an earlier schema-drift remediation had introduced incorrect graph wiring, the chatbot was explicitly asked to inspect the live upstream connections after applying this fix.

It reported:

`schema_validated upstream_nodes = ["baseline_raw"]`

and:

`deduped upstream_nodes = ["schema_validated"]`

Therefore, the relevant pipeline path remained:

`baseline_raw → schema_validated → deduped`

No additional upstream connection was reported during this remediation.

The chatbot also noted that `last_executed_code` still represented the previous execution because the patched node had not yet run.

The updated validation was stored in the live node configuration and therefore required another execution to verify its actual behaviour.

## Post-remediation execution

The exact same 12-column S3 input was retained for the retest.

No new dataset was uploaded.

The input still contained:

- All 11 original required columns
- The unexpected `Currency` column
- 12,575 rows
- `Currency = AUD` for all 12,575 rows

The pipeline was manually executed again.

This time the execution failed at `schema_validated`.

The reported error was:

`Schema validation failed: unexpected column(s) not in contract: ['Currency']`

This is the expected strict-schema behaviour.

The remediation therefore changed the behaviour from:

`12-column input → accepted → pipeline success → Currency exported`

to:

`12-column input → rejected at schema validation → no export`

## Post-remediation GCS validation

The GCS destination was refreshed after the failed execution.

Before remediation, the successful drift execution had created the fourth GCS object at approximately:

`12:16:45`

The remediated execution failed at approximately:

`12:22:36`

After that execution, the GCS bucket still contained the same four objects.

No fifth object was created.

This confirms that the invalid 12-column schema was prevented from reaching the destination after remediation.

## Status reporting observation

The post-remediation execution exposed an additional logging inconsistency.

The Logs panel clearly displayed a pipeline failure at `schema_validated`, and the pipeline summary reported an error status.

However, a green log entry stating:

`Pipeline execution completed successfully`

was also visible for the same execution period.

This creates conflicting execution signals:

- The detailed pipeline result reports failure.
- The schema-validation error identifies the unexpected `Currency` column.
- No GCS output was produced.
- A generic success-completion message was still emitted.

This could be misleading during production monitoring.

A user relying only on the generic completion message could incorrectly interpret the execution as successful even though the ETL workflow failed before producing output.

The detailed error and absence of a new GCS object provide stronger evidence of the actual execution outcome.

## Final result

**Unexpected column initially detected: NO**

**Unexpected column initially exported: YES**

**Initial pipeline warnings/errors: 0**

**Chatbot correctly diagnosed root cause: YES**

**Generated code matched original strict-schema intent before remediation: NO**

**AI Builder remediation applied: YES**

**Existing graph wiring preserved during this remediation: YES**

**Same Currency drift rejected after remediation: YES**

**Actionable error naming Currency produced: YES**

**Post-remediation GCS output created: NO**

**Conflicting success/error logging observed: YES**

## Key QA findings

This test produced three important findings.

First, the original AI-generated schema validator did not match its natural-language requirement. It was intended to enforce exactly 11 columns but implemented only a required-column presence check.

Second, the unexpected `Currency` column silently propagated through every downstream transformation and reached GCS without a warning. A successful pipeline status therefore did not guarantee compliance with the intended schema contract.

Third, AI Builder successfully corrected the validation when explicitly asked to compare the schema in both directions. The same input that previously passed was subsequently rejected with an actionable error identifying `Currency`.

However, the post-remediation execution also produced conflicting status messages by displaying both an explicit pipeline failure and a generic successful-completion message.

These results demonstrate the importance of independently validating AI-generated ETL logic, exported data, and execution status rather than relying solely on natural-language configuration or top-level success indicators.

## Chatbot quality

The chatbot performed well during the diagnosis of this drift case.

When explicitly instructed not to modify the pipeline, it correctly:

1. Inspected the generated validation code.
2. Identified that only missing columns were checked.
3. Identified the absence of extra-column validation.
4. Explained why `Currency` propagated through the pipeline.
5. Proposed strict schema-equality logic.

During remediation, it also reported the updated validation logic and live upstream connections before the pipeline was rerun.

Unlike the earlier wiring-remediation issue observed during another schema-drift test, this remediation did not require manual graph repair.

The final execution confirmed that the new validation behaviour worked as intended.

## Evidence

Evidence captured during this test includes:

- `datasets/drift_add_currency.csv`
- Verification of 12,575 input rows
- Verification of 12 input columns
- Confirmation that all original 11 columns remained present
- Confirmation of 12,575 `AUD` values
- Initial successful pipeline execution with 0 warnings and 0 errors
- Initial GCS output created at approximately 12:16:45
- Downloaded initial GCS output containing 12 columns
- Confirmation that `Currency` survived in all 12,575 output rows
- Chatbot inspection of the original generated validation code
- Chatbot diagnosis of the presence-only validation defect
- AI Builder remediation adding missing-column and extra-column checks
- Verification of live pipeline upstream connections after remediation
- Post-remediation failure at `schema_validated`
- Explicit error identifying `Currency` as unexpected
- GCS remaining at four objects after the failed remediated execution
- Conflicting failure and successful-completion log messages