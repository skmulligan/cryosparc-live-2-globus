#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path

CRYOSPARC_PREFIX = "/qb/rawdata/"


def parse_bool(value):
    """Convert common CSV boolean representations to True/False."""
    if value is None:
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
        "t",
    }


def parse_cryosparc_path(path):
    """
    Convert:

        /qb/rawdata/160230/20260713_exo05/epu_session/.../movie.eer

    into:

        project_id = 160230
        session_id = 20260713_exo05
        globus_path = 160230/20260713_exo05/epu_session/.../movie.eer
    """
    path = path.strip()

    if not path.startswith(CRYOSPARC_PREFIX):
        raise ValueError(
            f"Unexpected CryoSPARC path:\n"
            f"  {path}\n\n"
            f"Expected paths to begin with:\n"
            f"  {CRYOSPARC_PREFIX}"
        )

    relative_path = path[len(CRYOSPARC_PREFIX):]

    parts = Path(relative_path).parts

    if len(parts) < 3:
        raise ValueError(
            f"Could not determine project/session IDs from path:\n"
            f"  {path}"
        )

    project_id = parts[0]
    session_id = parts[1]

    return project_id, session_id, relative_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create a Globus batch manifest from a CryoSPARC Live "
            "exposure CSV."
        )
    )

    parser.add_argument(
        "csv_file",
        help="CSV exported from CryoSPARC Live",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output Globus batch manifest. "
            "If omitted, the filename is generated automatically."
        ),
    )

    filter_group = parser.add_mutually_exclusive_group()

    filter_group.add_argument(
        "--include-rejected",
        action="store_true",
        help=(
            "Include both accepted and rejected exposures. "
            "By default, only accepted exposures are included."
        ),
    )

    filter_group.add_argument(
        "--rejected-only",
        action="store_true",
        help=(
            "Create a manifest containing only rejected exposures. "
            "An exposure is rejected if Threshold Reject or "
            "Manual Reject is true."
        ),
    )

    parser.add_argument(
        "--allow-multiple-projects",
        action="store_true",
        help=(
            "Allow a manifest to contain files from multiple project IDs. "
            "By default, this is treated as an error."
        ),
    )

    parser.add_argument(
        "--allow-multiple-sessions",
        action="store_true",
        help=(
            "Allow a manifest to contain files from multiple session IDs. "
            "By default, this is treated as an error."
        ),
    )

    args = parser.parse_args()

    csv_file = Path(args.csv_file)

    if not csv_file.exists():
        raise SystemExit(
            f"Input file not found: {csv_file}"
        )

    movies = []
    project_ids = set()
    session_ids = set()

    accepted_count = 0
    threshold_only_count = 0
    manual_only_count = 0
    both_rejected_count = 0

    with csv_file.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        reader = csv.DictReader(f)

        required_columns = {
            "File Path",
            "Threshold Reject",
            "Manual Reject",
        }

        fieldnames = set(reader.fieldnames or [])
        missing = required_columns - fieldnames

        if missing:
            raise SystemExit(
                "Missing required CSV columns:\n  "
                + "\n  ".join(sorted(missing))
            )

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            file_path = row["File Path"].strip()

            if not file_path:
                continue

            threshold_reject = parse_bool(
                row["Threshold Reject"]
            )

            manual_reject = parse_bool(
                row["Manual Reject"]
            )

            rejected = threshold_reject or manual_reject

            if threshold_reject and manual_reject:
                both_rejected_count += 1

            elif threshold_reject:
                threshold_only_count += 1

            elif manual_reject:
                manual_only_count += 1

            else:
                accepted_count += 1

            # Decide whether this exposure belongs in the manifest.
            if args.rejected_only:
                if not rejected:
                    continue

            elif not args.include_rejected:
                if rejected:
                    continue

            try:
                project_id, session_id, globus_path = (
                    parse_cryosparc_path(file_path)
                )

            except ValueError as exc:
                raise SystemExit(
                    f"CSV line {line_number}:\n{exc}"
                )

            project_ids.add(project_id)
            session_ids.add(session_id)
            movies.append(globus_path)

    # Remove duplicate paths while preserving order.
    movies = list(dict.fromkeys(movies))

    if not movies:
        if args.rejected_only:
            raise SystemExit(
                "No rejected movies were found."
            )

        raise SystemExit(
            "No movies remain after filtering."
        )

    if (
        len(project_ids) > 1
        and not args.allow_multiple_projects
    ):
        projects = "\n  ".join(
            sorted(project_ids)
        )

        raise SystemExit(
            "\nERROR: Multiple project IDs were found "
            "in this CSV:\n\n"
            f"  {projects}\n\n"
            "No manifest was created.\n\n"
            "If this is intentional, rerun with:\n"
            "  --allow-multiple-projects"
        )

    if (
        len(session_ids) > 1
        and not args.allow_multiple_sessions
    ):
        sessions = "\n  ".join(
            sorted(session_ids)
        )

        raise SystemExit(
            "\nERROR: Multiple session IDs were found "
            "in this CSV:\n\n"
            f"  {sessions}\n\n"
            "No manifest was created.\n\n"
            "If this is intentional, rerun with:\n"
            "  --allow-multiple-sessions"
        )

    # Determine manifest type for automatic filename.
    if args.rejected_only:
        manifest_type = "rejected_movies"

    elif args.include_rejected:
        manifest_type = "all_movies"

    else:
        manifest_type = "accepted_movies"

    # Generate output filename automatically if not supplied.
    if args.output:
        output_file = Path(args.output)

    elif len(project_ids) == 1 and len(session_ids) == 1:
        project_id = next(iter(project_ids))
        session_id = next(iter(session_ids))

        output_file = Path(
            f"{project_id}_{session_id}_{manifest_type}.txt"
        )

    else:
        output_file = Path(
            f"{manifest_type}.txt"
        )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as f:

        for movie in movies:
            # Source and destination paths are intentionally identical
            # so the directory hierarchy is retained.
            f.write(
                f"{movie} {movie}\n"
            )

    total_rejected = (
        threshold_only_count
        + manual_only_count
        + both_rejected_count
    )

    print()
    print("CryoSPARC Live -> Globus Manifest")
    print("=================================")

    if len(project_ids) == 1:
        print(
            f"Project ID:             "
            f"{next(iter(project_ids))}"
        )
    else:
        print(
            "Project IDs:            "
            + ", ".join(sorted(project_ids))
        )

    if len(session_ids) == 1:
        print(
            f"Session ID:             "
            f"{next(iter(session_ids))}"
        )
    else:
        print(
            "Session IDs:            "
            + ", ".join(sorted(session_ids))
        )

    print()
    print(
        f"Accepted exposures:     {accepted_count}"
    )
    print(
        f"Threshold rejected:     {threshold_only_count}"
    )
    print(
        f"Manually rejected:      {manual_only_count}"
    )
    print(
        f"Rejected by both:       {both_rejected_count}"
    )
    print(
        f"Total rejected:         {total_rejected}"
    )

    print()
    print(
        f"Movies in manifest:     {len(movies)}"
    )
    print(
        f"Manifest:               {output_file}"
    )
    print()

    if args.rejected_only:
        print(
            "Manifest contains rejected exposures only."
        )

    elif args.include_rejected:
        print(
            "Manifest contains accepted and rejected exposures."
        )

    else:
        print(
            "Manifest contains accepted exposures only."
        )


if __name__ == "__main__":
    main()