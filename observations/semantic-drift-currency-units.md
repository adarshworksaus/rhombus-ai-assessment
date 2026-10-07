# Semantic Drift Test: Monetary Unit / Scale Change

## Test scenario

This test evaluated whether the Rhombus pipeline could detect semantic drift where the schema and data types remained valid but the meaning and scale of monetary values changed.

The original baseline contained monetary values such as:

`Price Per Unit = 18.5`

`Total Spent = 185.0`

A drifted dataset was created by multiplying every parseable value in both monetary columns by 100:

`Price Per Unit = 1850.0`

`Total Spent = 18500.0`

This simulates a unit/scale change such as values being represented in cents instead of dollars while retaining numeric data types.

The drifted dataset was saved as:

`datasets/drift_currency_units.csv`

## Drift construction

The drift changed:

- 11,966 non-empty `Price Per Unit` values
- 11,971 non-empty `Total Spent` values

The dataset still contained:

- 12,575 rows
- 11 columns
- The exact original column names
- Numeric monetary values
- No additional `Currency` column
- No structural schema change

Example changes included:

`18.5 → 1850.0`

`185.0 → 18500.0`

and:

`29.0 → 2900.0`

`261.0 → 26100.0`

The file was uploaded to the existing S3 object key:

`baseline.csv`

Therefore, the Rhombus source configuration remained unchanged.

## Expected behaviour

This drift was intentionally designed to be structurally valid.

The existing `schema_validated` node checks the exact 11-column schema, so it was expected to accept the file.

However, a robust data-quality pipeline could potentially identify that the monetary values had undergone a major distribution or unit change.

The purpose of this test was therefore to determine whether the AI-generated cleaning workflow detected semantic changes beyond schema and type validation.

## Execution result

The pipeline was manually executed with the semantic-drift dataset in S3.

The run started at approximately:

`12:33:57`

and completed at approximately:

`12:34:19`

Observed behaviour included:

- Pipeline execution started
- 8 transformations applied
- 12,575 rows processed
- Pipeline completed successfully
- Pipeline execution completed successfully

No warning or error was generated for the monetary scale change.

The exact 11-column schema passed `schema_validated`.

## GCS result

Before this test, the GCS bucket contained five output objects.

The semantic-drift execution created a sixth output object at approximately:

`12:34:17`

The generated object was:

`baseline_cleaned_1791336855072.csv`

This confirmed that the semantic drift passed through the complete pipeline and reached the configured destination.

## Independent output validation

The generated GCS output was downloaded and compared against:

`datasets/drift_currency_units.csv`

Records were matched using `Transaction ID`.

Validation results:

- Input rows: 12,575
- Output rows: 12,575
- Output columns: 11
- Original schema preserved
- Comparable rows where drifted monetary values survived unchanged: 11,362
- Comparable rows where Rhombus changed the monetary values: 0

The comparison required both `Price Per Unit` and `Total Spent` to be parseable for a record, so the comparable-row count is lower than the total dataset row count.

No claim is made about monetary correction for rows excluded from that comparison.

Examples of unchanged drifted values included:

`TXN_6867343`

`Price Per Unit: 1850.0 → 1850.0`

`Total Spent: 18500.0 → 18500.0`

---

`TXN_3731986`

`Price Per Unit: 2900.0 → 2900.0`

`Total Spent: 26100.0 → 26100.0`

---

`TXN_9303719`

`Price Per Unit: 2150.0 → 2150.0`

`Total Spent: 4300.0 → 4300.0`

Therefore, for every row included in the independent monetary comparison, Rhombus preserved the drifted values rather than correcting or flagging them.

## Result

**Schema drift present: NO**

**Data-type drift present: NO**

**Semantic monetary scale drift present: YES**

**Schema validation passed: YES**

**Pipeline completed successfully: YES**

**Warning generated for semantic drift: NO**

**Error generated for semantic drift: NO**

**GCS output created: YES**

**Comparable drifted values corrected by Rhombus: 0**

**Semantic drift automatically detected: NO evidence observed**

## Key QA finding

The pipeline successfully enforced structural schema requirements but did not identify this controlled semantic change in monetary scale.

The test demonstrates an important distinction between syntactic data quality and semantic data quality.

The values remained valid numeric values and retained the expected column names, meaning schema and type validation alone could not distinguish:

`18.5`

from:

`1850.0`

without additional knowledge about expected units, ranges, distributions, or historical behaviour.

For the 11,362 independently comparable records, the drifted monetary values were exported unchanged.

This demonstrates that a pipeline can complete successfully and produce structurally valid output while still allowing a significant semantic change to propagate to the destination.

## Evidence

Evidence collected for this test includes:

- `datasets/drift_currency_units.csv`
- 12,575-row input verification
- Exact 11-column schema verification
- Verification that 11,966 `Price Per Unit` values were scaled
- Verification that 11,971 `Total Spent` values were scaled
- Successful Rhombus execution
- 8 transformations applied
- 12,575 rows processed
- Sixth GCS output created at approximately 12:34:17
- Downloaded `baseline_cleaned_1791336855072.csv`
- Independent Transaction-ID-based comparison
- 11,362 comparable rows preserving drifted monetary values
- 0 comparable rows where Rhombus changed the monetary values

## Chatbot diagnosis

After the successful semantic-drift execution and independent GCS validation, the Rhombus chatbot was asked to inspect the current live pipeline without modifying it.

The chatbot concluded that none of the current pipeline nodes contain logic capable of detecting monetary scale or unit semantic drift.

It identified `schema_validated` as structural validation only. The node compares expected and actual column sets but does not inspect values, ranges, distributions, or units.

It also inspected `numeric_enforced` and reported that its relevant logic is:

```python
output_df[col] = pd.to_numeric(output_df[col], errors='coerce')
```

Therefore, this transformation validates numeric parseability rather than semantic reasonableness.

For example:

`18.5`

and:

`1850.0`

are both valid numeric values and therefore receive the same treatment.

### Missing semantic controls

The chatbot reported that the current pipeline contains no validation based on:

- Expected minimum or maximum monetary values
- Historical monetary distributions
- Baseline dataset statistics
- Percentile or statistical drift checks
- Inter-column monetary consistency
- Business-defined monetary units

It therefore correctly explained why the 100x scale change could pass all eight transformations without producing a warning or error.

### Inter-column invariant observation

The chatbot identified a possible business invariant:

`Price Per Unit × Quantity ≈ Total Spent`

However, it also correctly noted that this would not necessarily detect the controlled drift used in this test.

Both `Price Per Unit` and `Total Spent` were multiplied by 100 while `Quantity` remained unchanged.

Therefore, their mathematical relationship was intentionally preserved.

This means that detecting the controlled uniform scale change requires additional semantic context, such as expected ranges, known units, historical distributions, or comparison against a baseline.

### Recommended validation point

The chatbot recommended placing semantic monetary validation immediately after:

`numeric_enforced`

and before:

`date_standardized`

Its reasoning was that monetary values should first be converted into reliable numeric representations before performing range or statistical validation.

Potential semantic controls suggested by the chatbot included:

1. Business-defined monetary ranges.
2. Inter-column consistency validation.
3. Comparison of statistics such as mean, median, or p95 against a baseline distribution.

The chatbot also correctly stated that meaningful thresholds cannot be inferred reliably from structural schema information alone and would require either business-defined expectations or reference data.

## Chatbot quality

The chatbot diagnosis was accurate and appropriately scoped.

It correctly:

1. Distinguished structural validation from semantic validation.
2. Identified `numeric_enforced` as type coercion rather than magnitude validation.
3. Confirmed the absence of range, distribution, and baseline checks.
4. Explained why numerically valid 100x values passed the pipeline.
5. Identified the limitation of the `Price Per Unit × Quantity ≈ Total Spent` invariant for this particular controlled drift.
6. Recommended an appropriate location for semantic validation.
7. Made no pipeline changes when explicitly instructed to diagnose only.

Unlike some earlier remediation interactions, no unsupported claim about successful modification was made because this request was inspection-only.

## Final semantic-drift finding

This test demonstrates that successful schema validation and numeric type enforcement do not guarantee semantic correctness.

The pipeline successfully processed and exported a dataset whose monetary scale had changed by a factor of 100.

Independent output validation showed that 11,362 comparable records preserved the drifted monetary values unchanged, while the chatbot subsequently confirmed that no current transformation was designed to detect such a change.

The chatbot was able to diagnose the limitation after the fact, but the pipeline itself provided no automatic warning or error during execution.
