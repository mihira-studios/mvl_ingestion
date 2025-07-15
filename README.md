# MVL Ingestion Tool

A pipeline utility for ingesting image sequences and files (e.g., EXRs) from vendor deliveries into the MVL project workspace. Supports path resolution using project metadata, MOV generation, and optional proxy creation.

---

## Features

- Ingest files or folders from vendor deliveries
- Auto-generate source and destination paths using project, scene, and shot
- Context-aware fallback using `mvl_core_pipeline.context.Context`
- MOV creation from EXR sequences (via Gaffer or `mvl_make_dailies`)
- Proxy image generation (planned)
- CLI + API-compatible

---

## Requirements

- Python 3.7+
- mvl_core_pipeline
- mvl_make_dailies
- pandas
- requests

---

## Usage

### CLI

```bash
python ingest.py \
  --project gen63 \
  --vendor vendorA \
  --input_date 2025-07-14 \
  --scene SC_48 \
  --shot SH_14 \
  --input "j:/gen63/to_mvl/vendorA/20250714/SC_48/SH_14" \
  --output "j:/gen63/repo/sequences/SC_48/SH_14" \
  --resolution 4448x3096 \
  --proxy jpeg \
  --mov \
  --force
```

### Required CLI Arguments

| Flag           | Description                     |
| -------------- | ------------------------------- |
| `--project`    | Project name (default: `gen63`) |
| `--vendor`     | Vendor name                     |
| `--input_date` | Date of delivery (`YYYY-MM-DD`) |

### Optional Arguments

| Flag           | Description                                 |
| -------------- | ------------------------------------------- |
| `--input`      | Override input path                         |
| `--output`        | Output destination                          |
| `--scene`      | Scene name (e.g., `SC_48`)                  |
| `--shot`       | Shot name (e.g., `SH_14`)                   |
| `--proxy`      | Create proxy image (`jpeg`, `png`)          |
| `--mov`        | Generate `.mov` file from EXR sequence      |
| `--resolution` | Image resolution (`default: 4448x3096`)     |
| `--force`      | Force ingestion even if file already exists |

---

## 🧪 API Usage

```python
from ingest import IngestionHandler

args = {
    "project": "gen63",
    "vendor": "vendorA",
    "input_date": "2025-07-14",
    "scene": "SC_48",
    "shot": "SH_14",
    "resolution": "4448x3096",
    "proxy": "jpeg",
    "force": True
}

processor = IngestionHandler(args)
processor.run()
```

---

## Directory Template Config

File paths are generated using templates defined in your `path_template.yaml`.

Example:

```yaml
template:
  ingest_workspace: '{project_root}/to_mvl/{vendor}/{date}/{scene}/{scene_shot}/{resolution}'
  egress_worksapce: '{project_root}/from_mvl/{vendor}/{date}/{scene}/{scene_shot}/{resolution}'
  
```

These templates use variables like:

- `project_root`
- `vendor`
- `date`
- `scene`
- `shot`
- `repo` (e.g., `repo`, `publish`, etc.)

---

## 🛠️ Internals

- `VFXFileProcessor` handles all core logic:
  - Resolves paths via CLI or context
  - Copies files or sequences
  - Uses `path_template.yaml` via `resolve_template`
- `Context` fallback enables usage from within MVL environment
- Logging via `Logger` module

---

## 📟 License

**Internal Use Only.** Part of MVL Pipeline Tools. Do not distribute outside the studio.

---

## 👥 Authors

MVL Pipeline Tools Team\
📧 [support@mihira.studio](mailto\:support@mihira.studio)

