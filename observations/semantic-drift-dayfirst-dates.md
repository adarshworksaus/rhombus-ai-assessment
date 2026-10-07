# Semantic Drift Test: Day-First DD/MM/YYYY Dates

## Test scenario

This test evaluated a semantic date-format drift where the source changed from the previously tested month-first MM/DD/YYYY convention to day-first DD/MM/YYYY while retaining the same slash-separated structure.

The drift dataset is:

`datasets/drift_dates_dayfirst.csv`

Exactly 500 transaction dates were changed into ambiguous DD/MM/YYYY values where both the day and month were less than or equal to 12 and were different.

This makes the values structurally valid but semantically ambiguous.

Examples include:

- `08/04/2024`, intended as 8 April 2024
- `05/10/2022`, intended as 5 October 2022
- `07/05/2022`, intended as 7 May 2022

## Expected behaviour

The pipeline should not silently reinterpret ambiguous dates.

A safe implementation should either:

- enforce an explicit expected date format,
- detect the convention change and stop,
- or raise a warning requiring the source date convention to be confirmed.

The intended calendar meaning of each transaction date should be preserved.

## Actual behaviour

The pipeline completed successfully and exported an output artifact to GCS.

No pipeline error or warning identified that the source date convention had changed.

The date-cleaning implementation relied on parser inference rather than an explicit day-first format contract.

As a result, ambiguous DD/MM/YYYY values were interpreted using month-first behaviour.

## Independent validation

The output was validated using:

`data-validation/validate_pipeline.py`

The semantic date comparison failed.

Result:

- 500 deliberately changed dates tested
- 500 semantic date changes detected
- structural date validation still passed
- the pipeline reported successful execution

Examples detected by the validator included:

- `TXN_6867343`: baseline `2024-04-08` → output `2024-08-04`
- `TXN_9303719`: baseline `2022-10-05` → output `2022-05-10`
- `TXN_9458126`: baseline `2022-05-07` → output `2022-07-05`

The validation suite reported 9/10 checks passing, with the semantic date check failing.

This demonstrates that syntactically valid dates can still contain incorrect business meaning.

## Pipeline response

The pipeline did not stop.

It carried on through the cleaning workflow and produced output.

This is more dangerous than a hard failure because the resulting dates remain valid-looking ISO dates while representing different calendar dates.

## Chatbot diagnosis

The AI Builder correctly identified that the generated date-cleaning logic did not explicitly guarantee the expected source convention.

The implementation relied on pandas/parser inference and did not explicitly enforce the intended date format.

The diagnosis also identified the risk that a DD/MM/YYYY source could therefore be silently interpreted as MM/DD/YYYY for ambiguous values.

## Recommended remediation

The date-cleaning stage should use an explicit source-format contract rather than relying on automatic inference.

The pipeline should also validate whether incoming values conform to the expected convention and stop or warn when the convention changes.

For mixed or ambiguous source formats, the pipeline should avoid silently selecting an interpretation.

## Schedule behaviour

The drift was evaluated against the same configured ETL workflow.

The pipeline's schedule configuration remained active; no evidence showed that semantic date drift automatically disabled the schedule.

Because the pipeline itself accepted the drift, a scheduled execution could therefore propagate semantically incorrect dates unless an independent validation guard detects the issue.

## Severity

**Critical**

The pipeline completed successfully while changing the meaning of 500 transaction dates.

This creates a silent data-quality failure that downstream systems could consume without recognizing that the dates are incorrect.

## Reproducibility

1. Use `datasets/drift_dates_dayfirst.csv` as the source input.
2. Run workflow `5288`.
3. Allow the pipeline to complete and export the cleaned result.
4. Download the corresponding GCS output.
5. Run `data-validation/validate_pipeline.py` with the day-first drift dataset as input and the trusted baseline as the semantic reference.
6. Observe that structural validation succeeds but the semantic date comparison detects 500 changed date meanings.

## Final finding

The pipeline is not robust to a source convention changing from MM/DD/YYYY to DD/MM/YYYY when values remain structurally ambiguous.

The failure is silent: execution succeeds, output is produced, and the resulting dates remain syntactically valid.

Independent semantic validation is therefore necessary unless the pipeline explicitly enforces the source date convention.
