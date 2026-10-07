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

## Execution result

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

## GCS result

A new GCS output object was created at approximately:

`12:16:45`

This confirmed that the unexpected schema was allowed through the complete pipeline and reached the configured destination.

## Independent output validation

The newly generated GCS CSV was downloaded and inspected independently.

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