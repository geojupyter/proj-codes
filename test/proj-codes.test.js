import assert from "node:assert/strict";
import { test } from "node:test";

import projCodes from "../index.js";

test("generated artifact contains the expected number of CRS codes", () => {
  assert.equal(Object.keys(projCodes).length, 6990);
});

test("EPSG:4326 matches expected", () => {
  assert.deepEqual(projCodes["EPSG:4326"], {
    auth_name: "EPSG",
    code: "4326",
    name: "WGS 84",
    proj4string: "+proj=longlat +datum=WGS84 +no_defs +type=crs",
    area_of_use: [-180.0, -90.0, 180.0, 90.0],
  });
});
