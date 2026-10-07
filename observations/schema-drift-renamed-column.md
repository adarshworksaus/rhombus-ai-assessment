# Schema Drift Test: Renamed Column

## Test scenario

This test evaluated how the Rhombus pipeline responds when an expected source column is renamed while the overall number of columns remains unchanged.

The baseline dataset contains 11 columns, including:

`Price Per Unit`

For this drift case, the column was renamed to:

`Unit Price`

No rows were removed or added.

- Baseline rows: 12,575
- Drift rows: 12,575
- Baseline columns: 11
- Drift columns: 11
- Original column: `Price Per Unit`
- Renamed column: `Unit Price`

The drifted dataset was saved as:

`datasets/drift_rename_price_column.csv`

For the S3 test, it was uploaded using the existing object key:

`baseline.csv`

This ensured that the Rhombus source configuration itself was not changed.

## Expected behaviour

The pipeline was originally built against a fixed 11-column schema containing `Price Per Unit`.

Because `Price Per Unit` was renamed to `Unit Price`, I expected the pipeline to detect the schema mismatch rather than silently process the changed structure.

A production-safe response would be to fail before producing output and provide an actionable error identifying the missing expected column.

## Initial observed behaviour

During testing, an earlier run failed at the `deduped` node with:

`DataFrameDuplicateRowRemover.transform() got multiple values for argument 'keep'`

Investigation using the Rhombus chatbot indicated that the `deduped` node had incorrectly ended up with two upstream connections after the schema-validation remediation was introduced.

The intended path was:

`baseline_raw → schema_validated → deduped`

However, the original `baseline_raw → deduped` connection had initially remained alongside the new connection.

This produced a pipeline configuration error unrelated to the actual renamed-column drift.

## Chatbot remediation behaviour

The chatbot was used to diagnose and attempt to repair the pipeline.

Several important behaviours were observed:

1. The chatbot identified that the pipeline should validate the expected schema before performing downstream transformations.

2. A new AI-generated `schema_validated` node was introduced between the source and deduplication steps.

3. During remediation, the generated validation logic initially contained an incorrect expected column name and had to be corrected to require `Price Per Unit`.

4. Rewiring the pipeline also resulted in `deduped` temporarily having two upstream connections.

5. The chatbot subsequently reported that the duplicate connection had been removed, but the canvas still showed the invalid connection state.

6. The stale direct connection from `baseline_raw` to `deduped` ultimately had to be removed manually in the canvas.

This exposed a usability/reliability issue: the chatbot could report that a structural pipeline repair had succeeded even though the visual pipeline still showed an invalid configuration.

## Final pipeline configuration

After manually removing the stale connection, the relevant pipeline path became:

`baseline_raw → schema_validated → deduped → downstream cleaning transformations`

The schema validation node was configured to require the original 11 expected columns and to fail if any were missing.

It did not fabricate or restore missing columns.

## Final execution result

With the renamed-column dataset still present in S3, the pipeline was executed again.

This time the pipeline failed at `schema_validated` with the explicit error:

`Schema validation failed: missing required column(s): ['Price Per Unit']`

This correctly detected that the expected `Price Per Unit` column was absent even though the dataset still contained 11 columns and contained the replacement column `Unit Price`.

## GCS result

After the failed run, the GCS destination was refreshed.

No new output object was created.

The bucket continued to contain only the existing objects created at approximately:

- 00:41:53
- 11:10:19

There was no output corresponding to the renamed-column failure.

This is the desired fail-safe behaviour because a dataset violating the expected schema contract was prevented from reaching the destination.

## Result

**Schema drift detected: YES**

**Pipeline failed before export: YES**

**Actionable missing-column error produced: YES**

**Invalid output written to GCS: NO**

The final schema-validation behaviour is appropriate for a fixed-schema ETL pipeline: the pipeline fails early rather than silently accepting an unexpected column rename.

However, the remediation process exposed additional platform issues around AI-generated fixes and graph rewiring. In particular, chatbot-reported fixes did not always correspond to the actual canvas state and required manual verification and intervention.

## Key QA finding

The strongest finding from this test is not only that renamed-column drift can be detected, but that AI-assisted pipeline remediation itself requires verification.

The chatbot was useful for diagnosis, but its generated changes temporarily introduced an invalid graph configuration and it later reported that the wiring was corrected before the canvas actually reflected that state.

For production use, chatbot-generated pipeline repairs should therefore be validated against the live graph before being trusted as successfully applied.

## Schedule aftermath

The schedule remained available during testing. The drifted execution failed before the GCS output stage, so no new destination object was produced.

## Evidence

Evidence captured during this test includes:

- S3 upload confirmation for the drifted `baseline.csv`.
- Pipeline failure at `deduped` during the remediation process.
- Canvas state showing the duplicate upstream connection.
- Chatbot diagnosis and attempted repair.
- Final `schema_validated` failure identifying `Price Per Unit` as missing.
- GCS destination showing no new output object after the failed drift execution.