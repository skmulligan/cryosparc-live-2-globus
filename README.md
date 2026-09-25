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
collection_session_ID/epu_session/Images-Disc1/GridSquare_13043050/Data/movie.eer
```

Globus collections are shared by project, so both source and destination paths in the manifest start with the session ID. The project ID is retained for validation, reporting, and the output filename.

Default is accepted movies only, rejected flag appends rejected_movies to filename. The output filename is generated automatically from the project and session IDs:

```text
160230_collection_session_ID_accepted_movies.txt
160230_collection_session_ID_rejected_movies.txt
```


## Usage

```bash
python create_globus_manifest_PNCC.py cryosparc_live_export.csv
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

Use the project's shared collection as the source. The session directory and all directories beneath it are preserved at the destination.

## Options

Specify a custom output filename:

```bash
python create_globus_manifest_PNCC.py exposures.csv \
    -o custom_manifest.txt
```

Include rejected movies:

```bash
python create_globus_manifest_PNCC.py exposures.csv \
    --include-rejected
```

Export rejected movies:
```bash
python create_globus_manifest_PNCC.py exposures.csv \
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
create_globus_manifest_PNCC.py
     ↓
Globus batch manifest
     ↓
Download accepted raw movies only
```

This avoids transferring raw movies that were rejected during CryoSPARC Live processing.
