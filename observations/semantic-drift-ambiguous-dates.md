# Semantic Drift Test: Ambiguous Date Interpretation

## Test scenario

This test evaluated how the Rhombus pipeline handles semantically ambiguous date representations while preserving the expected schema.

The baseline dataset contained:

- 12,575 rows
- 11 columns
- 12,575 non-empty `Transaction Date` values
- Dates represented in ISO `YYYY-MM-DD` format

A controlled drift dataset was created by changing exactly 500 dates from ISO format into ambiguous slash-separated `MM/DD/YYYY` strings.

Only dates where both the month and day were <= 12 and different were selected. This ensured that each modified value could validly be interpreted in more than one way.

Examples:

`2024-04-08 → 04/08/2024`

`2022-10-05 → 10/05/2022`

`2022-05-07 → 05/07/2022`

The drifted dataset was saved as:

`datasets/drift_ambiguous_dates.csv`

The resulting dataset retained:

- 12,575 rows
- 11 columns
- Exact original schema
- 500 ambiguous slash-separated dates

## Expected behaviour

The test was designed to determine whether the date-cleaning transformation would:

- Preserve the original intended meaning
- Swap month and day
- Convert ambiguous values to missing
- Reject the input
- Warn about ambiguity

The original baseline provided a known ground truth for all 500 manipulated records.

## Execution result

The drifted dataset was uploaded to the existing S3 object key:

`baseline.csv`

The pipeline was manually executed.

The execution started at approximately:

`12:41:38`

and completed at approximately:

`12:42:00`

Observed behaviour:

- Pipeline execution started
- 8 transformations applied
- 12,575 rows processed
- Pipeline completed successfully
- Pipeline execution completed successfully
- No warning generated for date ambiguity
- No error generated for date ambiguity

A new GCS output was created.

The downloaded output was:

`baseline_cleaned_1791337316224.csv`

## Independent output validation

The output was independently compared with both the original baseline and the controlled drift dataset using `Transaction ID`.

Results:

- Manipulated dates: 500
- Original meaning preserved: 500
- Month/day meaning swapped: 0
- Converted to missing: 0
- Other transformation: 0

Examples:

`2024-04-08 → 04/08/2024 → 2024-04-08`

`2022-10-05 → 10/05/2022 → 2022-10-05`

`2022-05-07 → 05/07/2022 → 2022-05-07`

For this controlled MM/DD/YYYY test, all 500 manipulated dates were returned to their original ISO meaning.

This is a positive transformation result for the tested input convention.

## Chatbot diagnosis

After independent validation, the Rhombus chatbot was asked to inspect the current live generated code without modifying the pipeline.

It reported that `date_standardized` currently uses:

```python
parsed_dates = pd.to_datetime(
    input_df_1['Transaction Date'],
    infer_datetime_format=True,
    errors='coerce',
    utc=False
)
```

According to the chatbot inspection, the generated code does not explicitly provide:

- `format=`
- `dayfirst=`
- `yearfirst=`
- A documented MM/DD/YYYY contract
- A documented DD/MM/YYYY contract

Therefore, although all 500 controlled MM/DD/YYYY values were handled correctly in this execution, the generated transformation itself does not express the intended date convention explicitly.

## Remaining semantic risk

The chatbot identified a potential risk if a future source supplied ambiguous slash-separated dates using a different convention, such as DD/MM/YYYY.

For example:

`08/04/2024`

could mean 8 April 2024 under DD/MM/YYYY or August 4 2024 under MM/DD/YYYY.

The current generated code does not explicitly state which interpretation is contractually correct.

The chatbot also reported no explicit logic for:

- Detecting mixed date conventions
- Warning when a date is ambiguous
- Recording which format was inferred
- Reporting how many values were coerced to missing

These are code-inspection findings from the chatbot and should be independently tested before treating predicted parser behaviour as confirmed runtime behaviour.

## Current result

**Schema preserved: YES**

**Ambiguous dates introduced: 500**

**Pipeline completed successfully: YES**

**GCS output created: YES**

**Original meaning preserved in controlled MM/DD test: 500 / 500**

**Month/day swaps observed: 0**

**Dates converted to missing: 0**

**Warnings for ambiguity: 0**

**Explicit date-format contract in inspected code: NO**

## Key QA finding

The pipeline handled the controlled MM/DD/YYYY ambiguity test successfully: all 500 manipulated dates were restored to their original ISO meaning.

However, successful handling of this test does not establish that the transformation safely handles every ambiguous date convention.

The inspected generated code delegates parsing to `pd.to_datetime` without an explicit date-format contract.

The next controlled test should therefore reverse the slash-separated convention to DD/MM/YYYY while preserving the same original dates. This will independently establish whether the implementation safely handles a source convention change or silently changes date meaning.

## Follow-up controlled test: DD/MM/YYYY convention

A second controlled experiment was performed to independently test the date-format risk identified during the chatbot diagnosis.

The same original baseline was used, but the same type of 500 ambiguous dates were represented using `DD/MM/YYYY` instead of `MM/DD/YYYY`.

Examples:

`2024-04-08 → 08/04/2024`

`2022-10-05 → 05/10/2022`

`2022-05-07 → 07/05/2022`

The dataset was saved as:

`datasets/drift_dates_dayfirst.csv`

The dataset retained:

- 12,575 rows
- 11 columns
- Exact original schema
- 500 deliberately ambiguous DD/MM/YYYY dates

### Pipeline execution

The DD/MM dataset was uploaded to the same S3 source object.

The unchanged pipeline was manually executed.

Observed execution:

- Execution started at approximately 12:47:12 PM
- Execution completed at approximately 12:47:34 PM
- 8 transformations applied
- 12,575 rows processed
- Pipeline reported successful completion
- No date-ambiguity warning was observed for this run

A new GCS output was successfully created:

`baseline_cleaned_1791337650063.csv`

### Independent validation

The GCS output was compared against the original baseline using `Transaction ID`.

Results:

- Manipulated dates: 500
- Original meaning preserved: 0
- Month/day meaning swapped: 500
- Converted to missing: 0
- Other transformation: 0

This represents a 100% semantic corruption rate across the deliberately modified DD/MM test cases.

Examples:

`2024-04-08 → 08/04/2024 → 2024-08-04`

`2022-10-05 → 05/10/2022 → 2022-05-10`

`2022-05-07 → 07/05/2022 → 2022-07-05`

`2025-01-12 → 12/01/2025 → 2025-12-01`

The resulting values remained syntactically valid dates, meaning the corruption was not detectable through simple date-validity checks.

## Comparison of both date-convention tests

The two controlled experiments produced opposite outcomes:

| Input convention | Manipulated | Correct | Month/day swapped |
|---|---:|---:|---:|
| MM/DD/YYYY | 500 | 500 | 0 |
| DD/MM/YYYY | 500 | 0 | 500 |

The pipeline therefore handled the month-first convention correctly but did not preserve the intended meaning when the source convention changed to day-first.

Importantly, both runs:

- Preserved the expected schema
- Processed 12,575 rows
- Completed successfully
- Produced GCS output
- Did not surface a date-ambiguity warning

## Confirmed QA finding

This test confirms a silent semantic data-quality failure.

A source-system convention change from MM/DD/YYYY to DD/MM/YYYY can produce structurally valid but semantically incorrect dates while the pipeline still reports successful execution.

The existing `date_standardized` transformation does not encode an explicit source date-format contract or reject ambiguous slash-separated dates.

This means schema validation, row-count validation, and basic date-validity validation alone are insufficient to detect this failure.

Semantic validation against a declared date convention or trusted source contract is required.

## Chatbot diagnosis accuracy

The chatbot predicted that DD/MM/YYYY values could be interpreted incorrectly because the current generated transformation does not explicitly declare a day-first convention.

The controlled DD/MM experiment independently confirmed this prediction:

- Predicted risk: silent month/day semantic swap
- Observed result: 500 / 500 manipulated values swapped
- Pipeline status: successful
- Output produced: yes
- Ambiguity warning: none observed

This was therefore a useful and accurate diagnosis of the tested runtime behaviour.
