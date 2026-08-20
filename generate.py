"""Generate proj-codes.json and proj-codes.csv."""

import csv
import json
from pathlib import Path

from pyproj import CRS
from pyproj.database import query_crs_info
from pyproj.exceptions import CRSError

out_dir = Path("dist")


def build_crs_dict() -> dict[str, dict[str, str]]:
    """Build the CRS dictionary."""
    crs_list = query_crs_info(
        auth_name="EPSG",
        pj_types=None,
        allow_deprecated=False,
    )

    crs_dict = {}
    for crs in crs_list:
        try:
            proj4string = CRS.from_authority(crs.auth_name, crs.code).to_proj4()
        except CRSError:
            continue  # skips codes that can't be used in proj4js
        crs_id = f"{crs.auth_name}:{crs.code}"
        crs_dict[crs_id] = {
            "auth_name": crs.auth_name,
            "code": crs.code,
            "name": crs.name,
            "proj4string": proj4string,
            "area_of_use": (
                crs.area_of_use.west,
                crs.area_of_use.south,
                crs.area_of_use.east,
                crs.area_of_use.north,
            ),
        }
    return crs_dict


def main() -> None:
    """Write the CRS dictionary to disk."""
    crs_dict = build_crs_dict()

    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "proj-codes.json").open("w") as f:
        json.dump(crs_dict, f)

    with Path("proj-codes.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["auth_name", "code", "name"])
        for crs in crs_dict.values():
            writer.writerow([crs["auth_name"], crs["code"], crs["name"]])


if __name__ == "__main__":
    main()
