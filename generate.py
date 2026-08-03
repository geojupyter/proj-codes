from pyproj.database import query_crs_info

all_crs = query_crs_info(
    auth_name=None,
    pj_types=None,
    allow_deprecated=True,
)
