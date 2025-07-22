
# MVL Ingestion Tool

A pipeline utility for ingesting image sequences and files (e.g., EXRs) from vendor deliveries into the MVL project workspace.
Supports path resolution using project metadata, MOV generation, and optional proxy creation.

---

## Features

- Ingest files or folders from vendor deliveries
- Auto-generate source and destination paths using project, scene, and shot metadata
- MOV creation from EXR sequences (via Gaffer or `mvl_make_dailies`)
- Proxy image generation with resolution replacement in filenames
- Resolution presets like `2K (DCP)`, `4K UHD`, etc.
- CLI and API-compatible
- Optional parallel proxy and MOV generation

---

## Requirements

- Python 3.7+
- `mvl_core_pipeline`
- `mvl_make_dailies`
- `pandas`
- `requests`
- `OpenImageIO`
- `coloredlogs`

---
## Directory Template Config

File paths are generated using templates defined in your `path_template.yaml`.

Example:

```yaml
template:
  ingest_workspace: '{project_root}/to_mvl/{vendor}/{date}/{scene}/{scene_shot}/{resolution}'
  egress_worksapce: '{project_root}/from_mvl/{vendor}/{date}/{scene}/{scene_shot}/{resolution}'
```

---
## CLI Usage
CLI
ingest --help
usage: ingest.py [-h] [--no-gui] --input INPUT [--output OUTPUT] [--project PROJECT] [--input_date INPUT_DATE] [--vendor VENDOR] [--scene SCENE] [--shot SHOT] [--resolution RESOLUTION] [--no-force] [--proxy PROXY] [--no-proxy] [--no-mov] [--csv_path CSV_PATH]
                 [--proxy-res {2K_DCP,HD_1080,QHD_1440,4K_DCP,UHD_4K}]

MVL Ingestion Tool - Command-line utility to ingest files or image sequences (e.g. EXRs) from vendor deliveries into the pipeline's organized project structure. This tool can: - Copy raw assets (files or sequences) into their resolved destination folder - Resolve paths
based on project, scene, shot, and vendor - Generate MOV files from EXRs - Create proxy images in JPEG/PNG format - Handle contextual fallback using environment variables or CLI inputs Use --input to specify a direct path, or --project, --vendor, and --input_date to
auto-resolve source paths. Example: ingest --project gen63 --vendor from_da --input_date 2025-07-15 --scene SC_48 --shot SH_14

options:
  -h, --help            show this help message and exit
  --no-gui              Run application in GUI Mode.
  --input INPUT         The source directory to process.
  --output OUTPUT       The output directory for processed data.
  --project PROJECT     The name of the project.
  --input_date INPUT_DATE
                        Date in YYYYMMDD format.
  --vendor VENDOR       Vendor name to look into vendor/date directory.
  --scene SCENE         Scene name (e.g., SC_48). Used for path resolution and organizing shots.
  --shot SHOT           Shot name (e.g., SH_14). Used for path resolution and organizing plates.
  --resolution RESOLUTION
                        Resolution (e.g., 4448x3096).
  --no-force            Process on error.
  --proxy PROXY         Specify proxy file format (e.g., jpeg, webp).
  --no-proxy            Disable proxy creation.
  --no-mov              Generate MOV files from EXR.
  --csv_path CSV_PATH   csv file for scene and shot mapping .
  --proxy-res {2K_DCP,HD_1080,QHD_1440,4K_DCP,UHD_4K}
                        Preset resolution name from YAML. Options: 2K_DCP, HD_1080, QHD_1440, 4K_DCP, UHD_4K
---


## Resolution Presets

You can pass either a custom proxy resolution like `4448x3096` or a preset name. Presets include:

| Name         | Resolution   | Common Use         |
|--------------|--------------|--------------------|
| 2K (DCI)     | 2048x1080    | Cinema, VFX        |
| 1080p (FHD)  | 1920x1080    | Streaming           |
| 1440p (QHD)  | 2560x1440    | PC, YouTube        |
| 4K (DCI)     | 4096x2160    | Cinema, HDR        |
| 4K UHD       | 3840x2160    | TV, streaming      |

---

## CLI Usage

```bash
ingest --input "J:/gen63/vault/to_mvl/vendorA/20250714/SC_48/SH_14" --output "J:/gen63/repo/sequences/SC_48/SH_14" 
```

### Optional Flags

- `--no-proxy`: Disable proxy generation.
- `--no-mov`: Disable MOV generation.
- `--no-gui`: CLI-only mode.
- `--no-force`: Skip existing outputs unless forced.

---

## Output File Naming

Proxy filenames will have both `.exr` replaced and resolution strings like `4448x3096` substituted with the output resolution, e.g.:

```
plate_SC_48_SH_14_4448x3096.1001.exr
→ plate_SC_48_SH_14_2048x1080.1001.jpeg
```

---

## API Usage

```python
from mvl_ingestion.ingestion_processor import MVLIngestionProcessor

args = {
    "input": "C:/gen63/vault/to_mvl/da/20250330/SC_48/48_14/4448x3096",
    "output": "C:/Users/user/workspace/test_data/ingestion",
    "force": True,                  # equivalent to not using --no-force
    "use_proxy": True,              # equivalent to not using --no-proxy
    "proxy": "jpeg",                # or "webp"
    "proxy_res": "HD_1080",         # proxy resolution
    "mov": True,                    # equivalent to not using --no-mov
    "csv_path": "J:/gen63/vault/to_mvl/from_da/20250330/SC_48/shot_folders_to_be_renamed.csv",
    "gui": False                    # equivalent to --no-gui
}

processor = MVLIngestionProcessor(args)
processor.execute()
```

---

## 📟 License

**Internal Use Only.** Part of MVL Pipeline Tools. Do not distribute outside the studio.

---

## 👥 Authors

MVL Pipeline Tools Team\
📧 [support@mihira.studio](mailto\:support@mihira.studio)
