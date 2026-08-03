from pyproj import CRS
from pyproj.database import query_crs_info
from pyproj.exceptions import CRSError
import json

crs_list = query_crs_info(
    auth_name="EPSG",
    pj_types=None,
    allow_deprecated=False,
)

crs_dict = {}
for crs in crs_list:
    try:
        proj4string = CRS.from_epsg(crs.code).to_proj4()
    except CRSError:
        continue  # skips codes that can't be used in proj4js
    crs_dict[crs.code] = {
        "auth_name": crs.auth_name,
        "code": crs.code,
        "name": crs.name,
        "proj4string": proj4string
    }

with open("proj-codes.json", "w") as f:
    json.dump(crs_dict, f)