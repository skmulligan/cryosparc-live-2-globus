# CryoSPARC Live to Globus Manifest

Create a Globus batch-transfer manifest containing only accepted movies from a CryoSPARC Live CSV export.

The script reads CryoSPARC Live exposure metadata, excludes threshold-rejected and manually rejected exposures, converts CryoSPARC storage paths to Globus-relative paths, and writes a manifest suitable for `globus transfer --batch`.

Works with EPU collections and SerialEM collections.  Takes project ID and collection session ID from the CSV.

## Example

CryoSPARC Live path:

```text
/qb/rawdata/160230/collection_session_ID/epu_session/Images-Disc1/GridSquare_13043050/Data/movie.eer
```

Globus manifest path:

```text
160230/collection_session_ID/epu_session/Images-Disc1/GridSquare_13043050/Data/movie.eer
```

The output filename is generated automatically from the project and session IDs:

```text
160230_collection_session_ID_accepted_movies.txt
```

## Usage

```bash
python create_globus_manifest.py cryosparc_live_export.csv
```

The CryoSPARC CSV must contain these columns:

```text
File Path
Threshold Reject
Manual Reject
```

By default, an exposure is included only when both rejection fields are false.

## Globus Transfer

Use the generated file with the Globus CLI:

```bash
globus transfer \
    SOURCE_COLLECTION_ID:/ \
    DEST_COLLECTION_ID:/destination/ \
    --batch 160230_collection_session_ID_accepted_movies.txt
```

The original project/session directory structure is preserved.

## Options

Specify a custom output filename:

```bash
python create_globus_manifest.py exposures.csv \
    -o custom_manifest.txt
```

Include rejected movies:

```bash
python create_globus_manifest.py exposures.csv \
    --include-rejected
```

Export rejected movies:
```bash
python create_globus_manifest.py exposures.csv \
     --rejected-only
```

The script will stop if multiple project or session IDs are detected unless explicitly allowed:

```bash
--allow-multiple-projects
--allow-multiple-sessions
```

## Intended Workflow

```text
CryoSPARC Live
     ↓
Export exposure CSV
     ↓
create_globus_manifest.py
     ↓
Globus batch manifest
     ↓
Download accepted raw movies only
```

This avoids transferring raw movies that were rejected during CryoSPARC Live processing.
