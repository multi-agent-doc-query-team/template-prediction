# Monitoring Template and Unit Conversion API

This project runs one local service with two main jobs:

- **Choose a monitoring template** from an activity, well name, and service provider.
- **Provide a conversion formula** from a source unit, such as feet or pounds per gallon, to its SI equivalent.

An API is a way for another program to ask this service a question and receive a structured answer. You can also try it yourself using the browser page included with the project.

## 1. What happens when you use it?

### Template prediction

You provide the activity, well, and company. The application checks the information against its dataset, uses the saved prediction model, and returns a matching monitoring template, its confidence score, and whether the result needs review.

### Unit conversion

You provide a sensor name, a value, and its source unit. The application looks up the verified unit mapping and returns the target unit plus four calculation instructions.

For example, **10 feet becomes 3.048 metres**. The API returns the formula instructions; it does not include the calculated value in its response.

**Pint calculates the physical conversion factors during each live request.** The application loads approved source-unit expressions and explicit special-unit definitions into one Pint registry at startup. It reuses that registry and the parsed source units, but calls Pint again to calculate each requested formula. It does not use saved numeric factors as a fallback if Pint fails.

`app/utils/unit_conversion/runtime.py` coordinates the conversion.
`validation.py` checks the reading and its measurement type, and
`pint_engine.py` calculates the physical formula. Approved unit names,
dimensions, SI targets and 58 special Pint definitions are stored together in
`data/unit_conversion/unit_catalog.json`. The live catalog contains no saved
multiply/divide/add/subtract factors. Aliases are explicitly listed in
`aliases.py`. Passthrough labels return identity instructions.

Check `GET /api/v1/telemetry/health`: `conversion_engine` should be `pint`, and `pint_version` should be `0.26.1` after restarting the main API.

The normal conversion endpoint uses stored, verified mappings. It does not ask an AI model during a request, and it does not need a company name.

Current coverage is:

| Result | Number of source-unit labels |
| --- | ---: |
| SI conversion formula available | 1,466 |
| Keep the original value unchanged (passthrough) | 4 |
| Unsupported | 34 |
| **Total** | **1,504** |

Some labels are alternative spellings of the same unit, so these counts do not mean 1,504 different physical quantities. The conversion health page shows the current counts if mappings change later.

## 2. Folder structure

```text
unit_conv/
|-- main.py                         Starts the main application
|-- requirements.txt                Python packages needed by the application
|-- README.md                       This guide
|
|-- app/                            Application code
|   |-- api/                        Application setup, errors, and routers
|   |   |-- application.py          Builds the main API and loads shared resources
|   |   |-- exception_handlers.py   Formats API errors
|   |   `-- routers/               Template and unit-conversion endpoints
|   |-- schemas/                    Rules for accepted inputs and returned answers
|   |-- services/                   Template prediction and conversion logic
|   |-- repositories/               Loads and indexes template source files
|   |-- utils/unit_conversion/      Resolve, validate, calculate with Pint, format
|   |-- ml_predictor.py             Uses the saved template prediction model
|   `-- web/                        Existing web resources
|
|-- models/                         Saved template prediction files
|   |-- template_model.joblib
|   `-- vectorizer.joblib
|
|-- data/                           Reference information
|   |-- dataset.csv                 Dataset used to check template inputs
|   |-- templates.json              Monitoring templates
|   |-- unit_conversion/            Original references and generated unit_catalog.json
|   `-- ...                         Other existing reference files
|
|-- output/                         Results and reports
|   |-- SI_Unit_API_Support_Combined.xlsx
|   |-- API_All_Unit_Test_Inputs.zip
|   |-- API_Unit_Test_Responses/     Exact saved API responses
|   |   |-- supported_*.json
|   |   |-- unsupported_01.json
|   |   |-- run_summary.json        Test outcome, HTTP statuses and checksums
|   |   |-- input_manifest.json     Reference copy of the input manifest
|   |   `-- with_source_units/      Readable response copies including source_unit
|
|-- docs/ARCHITECTURE.md             Responsibilities and request workflows
|-- project_backups/                 Recovery copies and archived development tools
|-- .venv/                          Local Python environment, created during setup
`-- ...                             Existing local configuration files
```

All running API code is inside `app/`, started by `main.py`. There is no separate unit-conversion application and no `unit_mapping_lab` folder.

Keep the original source workbooks, reference files and models. Normal API requests do not modify them. Loose testing folders and offline tools have been removed from the working project and preserved in `project_backups/development_archives/Archived_Development_Tools.zip`.

## 3. Set up the project on Windows

The project has been tested with **Python 3.12**. Use Command Prompt (**CMD**) for the commands below.

### Step 1 â€” Open the project folder in CMD

For the current computer:

```cmd
cd /d "C:\Users\MuhammedSaidali\Desktop\Haliburton-RTWE\unit_conv"
```

If you saved the project somewhere else, replace the path with that folder. You should see `main.py` and `requirements.txt` there.

### Step 2 â€” Check Python

```cmd
py -3.12 --version
```

If Windows cannot find Python 3.12, install it before continuing. Open a new CMD window after installing it.

### Step 3 â€” Create the local environment

Run this once on a new computer, or if `.venv` is missing:

```cmd
py -3.12 -m venv .venv
```

This creates a project-specific place for Python and its packages. The commands in this guide use it directly, so you do not need to activate it or change PowerShell settings.

### Step 4 â€” Install the required packages

```cmd
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

This one file includes the application, automated-test, and mapping-audit libraries.
You do not need a second installation command for tests or audits.

### Step 5 â€” Check the template model files

Both of these files must be supplied with the project:

```text
models/template_model.joblib
models/vectorizer.joblib
```

Also keep `data/dataset.csv` and `data/templates.json`. Installing Python packages does not create these files. The model files are excluded from Git, so a fresh download of the repository may need them supplied separately.

You do not need to train a new model for normal use. Ollama does not need to be running for template prediction or the verified unit-conversion endpoint.

## 4. Start and stop the API

From the project folder, run:

```cmd
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Leave that CMD window open while using or testing the API.

Open this address in your browser:

**http://127.0.0.1:8000/docs**

This page lists the available actions and lets you send requests without writing code. The address is local to your computer.

To stop the API, click its CMD window and press **Ctrl+C**. After changing application code or mappings, stop it and start it again.

## 5. Try unit conversion in the browser

1. Start the API and open the documentation page above.
2. Expand **POST /api/v1/telemetry/convert**.
3. Click **Try it out**.
4. Replace the example input with the following JSON.
5. Click **Execute** and read the response below it.

```json
{
  "readings": [
    {
      "mnemonic": "DEPTH",
      "value": 10,
      "source_unit": "ft",
      "unit_type": null
    },
    {
      "mnemonic": "TEMP",
      "value": 25,
      "source_unit": "degC",
      "unit_type": null
    }
  ]
}
```

| Input field | Meaning |
| --- | --- |
| `mnemonic` | The name or identifier of the reading, such as `DEPTH` |
| `value` | A number for a physical measurement |
| `source_unit` | The exact source-unit label, such as `ft` or `degC` |
| `unit_type` | The measurement category, such as `length`; use `null` when you want the API to identify it from the mapping |

The API also accepts `Mnemonic` or `sensor` instead of `mnemonic`. Unit spelling and capitalization matter. A request can contain **1 to 50 readings**.

### Understanding the conversion answer

The answer contains `converted_values`, with one set of instructions for each accepted reading:

| Response field | Meaning |
| --- | --- |
| `sensor` | The reading's identifier |
| `target_unit` | The resulting unit, such as `meter` or `kelvin` |
| `unit_type` | The measurement category |
| `multiply` | Multiply the input value by this number |
| `divide` | Divide the result by this number |
| `add` | Add this number |
| `subtract` | Subtract this number |

Apply the instructions in this order:

```text
Converted value = (input value Ã— multiply Ã· divide) + add âˆ’ subtract
```

For the examples above, the calculated answers are **3.048 metres** and **298.15 kelvin**.

If any reading has an unsupported unit or a conflicting measurement category, the request returns an error instead of partial results. An HTTP **422** response means the request could not be accepted; its error details explain which reading failed.

### Values that stay unchanged

These four source labels are accepted as passthrough:

```text
DateTime
date time
datetime
NONE
```

They retain their original target label and return `unit_type: "passthrough"`. Keep their input value unchanged; do not apply arithmetic to a timestamp or other text.

This does not convert a date to another timezone, interpret its format, or assume that a missing unit is physically dimensionless.

Gauge pressure remains gauge pressure. Gas-volume conversions retain the source reference conditions; they do not change temperature, pressure, or gas conditions.

## 6. Try template prediction

On the same browser page, expand **POST /api/v1/templates/classify**, click **Try it out**, and use:

```json
{
  "activity_name": "Drill Ahead - Rotating",
  "well_name": "Well BH 69",
  "service_provider": "Halliburton Worldwide"
}
```

This is a tested example from the supplied dataset. The response includes the predicted template, confidence, and a `needs_review` flag. If `needs_review` is true, the application's existing prediction rules have flagged that result for review.

Use activity, well, and provider combinations present in the supplied dataset. A unit-conversion request does not need these three template-prediction fields.

## 7. Archived development tools and tests

The working folders contain the running application and its required data.
Loose `tests/`, `scripts/`, sample inputs, and mapping reports have been removed.

The current development tools are preserved in
`project_backups/development_archives/Archived_Development_Tools.zip`.
All 110 archived files were verified before the loose copies were removed.
Extract this ZIP into the project root only when maintenance or regression
testing is needed. Normal API startup does not require it.

Older output files, including the mnemonic catalog and intermediate JSON
reports, are preserved in `project_backups/Archived_Output_Files.zip`.
Previous development archives and test packages are stored under
`project_backups/development_archives/`.

The output folder now keeps only:

- `SI_Unit_API_Support_Combined.xlsx`: current combined support workbook.
- `API_All_Unit_Test_Inputs.zip`: portable inputs for all source labels.
- `API_Unit_Test_Responses/`: exact saved responses and annotated copies.

You can test manually at **http://127.0.0.1:8000/docs**. The portable input ZIP
contains its own runner if you want to repeat the complete API checks.

## 8. Available API actions

| Address | What it does |
| --- | --- |
| `GET /health` | Confirms that the main application responds |
| `GET /api/v1/telemetry/health` | Shows conversion counts and the mapping version |
| `POST /api/v1/templates/classify` | Predicts a monitoring template |
| `POST /api/v1/telemetry/convert` | Returns verified SI formulas or explicit passthrough instructions |

The main application exposes exactly two business endpoints: template classification and Pint unit conversion. Health checks and API documentation remain available. The retired AI-conversion implementation and catalog-only prediction fallback have been removed. Ollama is not required by the main pipeline. The archived prediction-check script tests the saved ML model.

## 9. Common problems

| What you see | What to do |
| --- | --- |
| Python or `py` is not recognized | Check that Python 3.12 is installed, then open a new CMD window. |
| `.venv\Scripts\python.exe` cannot be found | Open CMD in the project folder and complete the environment-creation step. |
| A Python package is missing | Run the package-installation command using `.venv\Scripts\python.exe`. |
| The browser or test runner cannot connect | Start the main API and leave that CMD window open; check the port number. |
| Port 8000 is already in use | Use the API already running there, or stop that instance with Ctrl+C before starting another. |
| Template prediction cannot load a model | Check that both `.joblib` files exist in `models/`. |
| A well, activity, or provider is rejected | Use a combination included in `data/dataset.csv`. |
| A unit returns `unsupported` | Check its exact spelling, then consult the workbook's **API Cannot Handle** sheet. |
| A supplied `unit_type` conflicts with the unit | Correct the category or use `null` so the mapped category is used. |
| A test package does not match the API version | Restart the API after changes; restore the maintenance archive, then regenerate inputs with `python -m scripts.make_api_test_inputs` if the approved mappings changed. |

For mapping maintenance, restore `scripts/` and `output/unit_mapping/` from `project_backups/development_archives/Archived_Development_Tools.zip`. Building or compiling mappings is a maintenance operation; normal setup only requires installing packages and starting `main:app`.

## 10. Detailed conversion accuracy audit

The latest audit corrected the tropical-year convention (`a[t]`) and improved
Fahrenheit factor precision. All 1,466 SI formulas passed an independent Decimal
reference reconstruction and 14,660 checks of their actual saved responses.
Definitions, feed conventions, source limitations and the two numeric corrections
are documented in the accuracy review at `output/unit_mapping/CONVERSION_ACCURACY_REVIEW.md` inside `project_backups/development_archives/Development_Archive.zip`.

After restoring the maintenance tools from the archive and running the API tests, verify the saved responses independently:

```cmd
.venv\Scripts\python.exe -m scripts.unit_mapping.audit_reference_formulas
.venv\Scripts\python.exe -m scripts.unit_mapping.audit_saved_conversion_responses
```

Restart an already running API after installing these corrected mappings.

## Architecture and regression checks

The current main folder structure is retained. Routes handle web requests,
services apply the business rules, repositories read the template files, and
the existing unit utilities calculate physical conversions with Pint. See
[the architecture guide](docs/ARCHITECTURE.md) for the detailed workflow.

Project paths are defined in `app/utils/constants.py`. They are calculated from
the project location, so moving the folder does not require editing machine-specific
paths. Template and validation dataset environment overrides remain supported
through `app/utils/config.py`.

Template data and the saved model load once per application worker. Restart the
server after changing data, models, or mappings.

To repeat development checks, first restore `project_backups/development_archives/Archived_Development_Tools.zip` into the project root. Then run:

```cmd
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

These include a comparison against 121 saved pre-refactor API scenarios covering
all 1,504 source labels and 90 realistic template/conversion cases.

A full verified copy of the project before the architecture changes is kept in
`project_backups/before_architecture_refactor/`. Keep this recovery copy until
you are satisfied with the updated project.


### Simplified unit-conversion folder

The live flow is: **resolve the source unit → validate its meaning → calculate
with Pint → format the response**.

The previous large `runtime_units.py` and `pint_definitions.py` files have been
replaced by the single JSON catalog. The offline audit lookup is separate from
the live converter. Special Pint units now have descriptive internal names such
as `rtwe_ccgr` rather than numbered identifiers.

No changes are needed to your API requests or response fields. Restart the server
to load the simplified code.
