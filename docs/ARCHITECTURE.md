# Application architecture

The existing main folder structure is retained. There are two business endpoints,
served by `main:app`: template classification and telemetry unit conversion.

## Responsibilities

| Location | Responsibility |
| --- | --- |
| `main.py` | Expose the ASGI application to Uvicorn |
| `app/api/application.py` | Build the application, register routes, initialize resources |
| `app/api/exception_handlers.py` | Format public HTTP errors and log unexpected failures |
| `app/api/routers/` | Accept requests and assemble public API responses |
| `app/schemas/` | Validate request fields and define response contracts |
| `app/services/` | Apply template selection and conversion batch policies |
| `app/services/tools/predictor.py` | Load the configured predictor adapter |
| `app/repositories/` | Read and index the template files |
| `app/ml_predictor.py` | Run the existing saved classification model |
| `app/utils/constants.py` | Central project directories and default file paths |
| `app/utils/config.py` | Resolve environment overrides for template data paths |
| `app/utils/unit_conversion/` | Validate unit meanings, call Pint, and render SI labels |
| `data/` and `models/` | Preserve the reference sources and trained artifacts |
| Archived `scripts/` | Offline tools in the development ZIP; absent from the working folders |
| Archived `tests/` | Regression checks and fixtures in the development ZIP |
| `output/` | Saved responses, workbooks, reports, and development archives |
| `project_backups/` | Local recovery copy; excluded from Git |

## Template request workflow

1. The schema validates the three input fields.
2. The service checks the normalized provider, activity, and well combination
   against an indexed snapshot of the validation dataset.
3. The existing classifier predicts a template ID and confidence using the same
   input text and model artifacts as before.
4. The repository returns a copy of that template. Consumers cannot modify the
   shared in-memory template snapshot.
5. The route returns the existing response and review flag.

The dataset remains an input allow-list. The expected dataset label is used to
flag disagreement with the prediction; it does not replace the classifier.
This refactor does not add provider-specific mnemonic mapping to templates.

## Conversion request workflow

1. The schema validates 1–50 readings.
2. The converter resolves an exact, case-sensitive source label and validates
   any supplied measurement type. Only explicit aliases are accepted.
3. For each supported physical source, Pint calculates the scale and offset
   against the approved SI target during that request.
4. The presentation helper supplies the readable SI label.
5. The service returns the complete batch. If any reading fails, it raises a
   structured business error and the HTTP layer returns the existing 422 body.

The four explicit passthrough labels retain identity instructions. They are
not physical SI conversions. Unsupported and ambiguous labels remain rejected.
No live AI service or network request is involved.

## Resource lifecycle

Template files, the configured prediction adapter, the default saved model, and
the Pint registry are initialized once per worker before accepting traffic.
They are also lazily available to direct Python callers. Restart the service
after changing templates, the dataset, models, unit definitions, or configuration.
Each worker owns its own cached resources. Conversion formulas are never cached.

The generated `data/unit_conversion/unit_catalog.json` is the single deployment
catalog for native source labels. Each physical entry contains a name, dimension,
SI target, and approved Pint expression. The same catalog contains the 58 custom
Pint definitions using descriptive names. A content fingerprint detects accidental
catalog corruption at load time. It is a consistency check, not an authenticity
signature or proof that a definition is scientifically correct.

The live catalog contains no stored response coefficients. Original reference
factors remain in the offline audit catalog and frozen regression fixtures.

Within the existing unit-conversion folder:

| File | Responsibility |
| --- | --- |
| `runtime.py` | Coordinate resolution, validation, and Pint calculation |
| `catalog.py` | Load and validate the generated unit data once |
| `aliases.py` | Explicit source spellings, feed conventions, and rejected labels |
| `validation.py` | Validate readings and supplied measurement types |
| `pint_engine.py` | Build the registry and calculate each physical formula |
| `unit_types.py` | Measurement type definitions and resolved response types |
| `dimensions.py` | Parse physical dimensions |
| `presentation.py` | Render readable SI target labels |

`RuntimeConverter` uses these functions directly. It no longer inherits from the
offline formula lookup. The archived offline `scripts/unit_mapping/convert.py` deliberately
reads audit coefficients and is not imported by the running API.

## Findings addressed

- Repeated CSV scans were replaced with one repository snapshot and indexed checks.
- Model and Pint registry construction no longer happens simply by importing the
  service modules.
- HTTP error formatting was removed from the conversion service.
- SI label presentation was separated from conversion batch policy.
- Application construction and error handling were separated from the entry point.
- Unexpected prediction and request failures now produce server-side logs.
- Large generated Python tables were replaced with one data-only JSON catalog.
- Live conversion no longer inherits an offline coefficient lookup.
- Mutable response-schema defaults were replaced with a field factory.

## Verification and preservation

The loose tests and offline tools were archived after verification. To restore them,
extract `project_backups/development_archives/Archived_Development_Tools.zip` into
the project root. Then run:

```cmd
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

The contract fixture freezes 121 HTTP scenarios from the application before the
refactor: all 1,504 source labels and 90 realistic conversion/classification cases.
Tests compare status codes and complete parsed response bodies. Other tests check
live Pint calls, failure behavior, independent reference arithmetic, semantic
distinctions, and preserved data/model fingerprints. This proves compatibility
and checks the existing numerical references; it is not a new independent
certification of the underlying unit definitions.

The full pre-refactor copy is in
`project_backups/before_architecture_refactor/`. Its manifest records the hashes
of 13,104 verified files. Stop the server before restoring a backup. Keep this
folder local because the complete copy includes environment configuration.

## Working-folder cleanup

The runtime does not import tests, training scripts, mapping builders, or output
reports. Loose development files were archived with verified SHA-256 fingerprints
before removal. The `output/` folder retains the combined support workbook, the
portable API input package, and the exact saved response folder. Original inputs,
models, runtime code, generated unit data, and configuration are preserved.
