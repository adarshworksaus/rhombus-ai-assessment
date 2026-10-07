# Data Validation Results

This document records the validation outcomes observed while testing the Rhombus S3-to-GCS pipeline.

The validation suite compares successful GCS exports against the corresponding S3 input and, where applicable, the trusted baseline dataset.

For drift cases that were rejected by `schema_validated`, no GCS artifact was produced for downstream validation. These cases are recorded as **Not applicable - stopped before export** rather than being reported as validation passes.

## Results

| Scenario | Source dataset | Pipeline result | Validation result | Key finding |
|---|---|---|---|---|
| Baseline | `baseline.csv` | Exported | PASS 11/11 | Schema, cleaning rules and semantic checks passed |
| Baseline repeated run | `baseline.csv` | Exported | PASS | Canonical hashes matched across repeated runs |
| Dropped column | `drift_drop_category.csv` | Stopped at schema validation | Not applicable - stopped before export | Missing `Category` rejected |
| Renamed column | `drift_rename_price_column.csv` | Stopped at schema validation | Not applicable - stopped before export | Missing expected `Price Per Unit` rejected |
| Quantity type drift | `drift_quantity_type.csv` | Exported | PASS 10/10 | 100 invalid quantities were converted to missing values without fabricated numeric replacements |
| Added column - before exact-schema guard | `drift_add_currency.csv` | Exported | FAIL 9/10 | Validator detected unexpected `Currency` column |
| Added column - after exact-schema guard | `drift_add_currency.csv` | Stopped at schema validation | Not applicable - stopped before export | Unexpected column rejected before export |
| Combined schema drift | `drift_combined_schema.csv` | Stopped at schema validation | Not applicable - stopped before export | Missing and unexpected columns detected together after chatbot remediation |
| Monetary semantic drift | `drift_currency_units.csv` | Exported | FAIL 9/10 | 23,937 monetary values changed scale, predominantly by 100x |
| Ambiguous MM/DD date control | `drift_ambiguous_dates.csv` | Exported | Semantic meaning preserved | 500 reformatted dates retained baseline meaning |
| Day-first DD/MM semantic drift | `drift_dates_dayfirst.csv` | Exported | FAIL 9/10 | 500 dates changed semantic meaning |

## Baseline Validation

The baseline validation completed with:

- 11/11 checks passed.
- 12,575 input rows and 12,575 output rows.
- Exact expected 11-column schema.
- Zero duplicate output rows.
- Zero missing required identifiers.
- Zero whitespace violations.
- Zero invalid numeric values.
- Zero invalid date-format values.
- Zero date-semantic changes.
- Zero monetary-scale changes.
- Zero invalid boolean values.
- Deterministic canonical output across repeated runs.

Overall result: **PASS**

## Quantity Type Drift

The quantity-type drift replaced 100 non-empty `Quantity` values with `INVALID_QUANTITY`.

The resulting output contained 100 additional missing Quantity values compared with the normal baseline output.

Validation completed with 10/10 checks passed. The pipeline therefore handled the invalid numeric values according to the cleaning rule without fabricating replacement quantities.

Overall result: **PASS**

## Added Currency Column

A historical run before the exact-schema guard exported all 12 input columns, including the unexpected `Currency` column.

The validator reported:

- 9/10 checks passed.
- Exact-schema validation failed.
- Unexpected column: `Currency`.

Overall result: **FAIL**

After exact-schema validation was introduced, the same schema drift was rejected before export.

## Monetary Semantic Drift

The monetary drift multiplied monetary values by 100 while retaining structurally valid numeric data.

The pipeline completed and exported the data, but semantic validation detected:

- 23,937 monetary scale changes.
- Example ratios of 100x in `Price Per Unit` and `Total Spent`.
- All structural and formatting checks still passed.

Overall result: **FAIL**

This demonstrates why structural validation alone is insufficient for semantic drift.

## Date Semantic Drift

Two date-format scenarios were tested.

The MM/DD control changed 500 source date representations while preserving their intended baseline meaning.

The DD/MM variant was structurally valid and the pipeline completed, but semantic validation detected exactly 500 changed date meanings.

Examples included:

- `2024-04-08` becoming `2024-08-04`.
- `2022-10-05` becoming `2022-05-10`.
- `2022-05-07` becoming `2022-07-05`.

Overall result for DD/MM semantic drift: **FAIL**

## Schema-Rejected Runs

The dropped-column, renamed-column, post-remediation added-column, and combined-schema scenarios stopped at `schema_validated`.

Because execution stopped before the GCS export stage, there was no drifted output artifact to compare against the S3 input.

These scenarios are intentionally recorded as:

**Not applicable - stopped before export**

rather than assigning a misleading validation pass.

## Determinism

Repeated clean baseline executions produced matching canonical output hashes.

The validator reported:

`first=de1b01cb53b49069..., second=de1b01cb53b49069...`

This confirms deterministic cleaned output for repeated executions of the same baseline input.
