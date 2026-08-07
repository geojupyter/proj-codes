# proj-codes

## About
proj-codes is a javascript package that provides a list of authority-defined coordinate reference systems and their cooresponding Proj4 codes. 

Explore avaliable CRS's [here](proj-codes.csv).

## Installation

```sh
npm install proj-codes
# or: pnpm add proj-codes
```

Requires a runtime with support for JSON import attributes (Node.js 20.10+, or a
bundler that handles `with { type: 'json' }`).

## Usage

The package exports a single object keyed by `AUTHORITY:CODE`:

```js
import projCodes from 'proj-codes';

projCodes['EPSG:4326'];
// {
//   auth_name: 'EPSG',
//   code: '4326',
//   name: 'WGS 84',
//   proj4string: '+proj=longlat +datum=WGS84 +no_defs +type=crs'
// }
```

Both a default and a named export are available, and the raw JSON can be
imported directly:

```js
import projCodes from 'proj-codes';                    // default
import { projCodes } from 'proj-codes';                // named
import projCodes from 'proj-codes/proj-codes.json' with { type: 'json' };
```

### Entry shape

| Field | Type | Description |
| --- | --- | --- |
| `auth_name` | `string` | Authority name, currently always `"EPSG"` |
| `code` | `string` | Authority code, e.g. `"4326"` |
| `name` | `string` | Human-readable CRS name, e.g. `"WGS 84"` |
| `proj4string` | `string` | PROJ.4 definition string |

Only non-deprecated EPSG CRS's that can be expressed as a PROJ.4 string are
included (~7,000 entries).

### With proj4js

Look up a definition and hand it to [proj4js](https://github.com/proj4js/proj4)
to transform coordinates:

```js
import proj4 from 'proj4';
import projCodes from 'proj-codes';

proj4.defs('EPSG:3857', projCodes['EPSG:3857'].proj4string);

proj4('EPSG:4326', 'EPSG:3857', [-122.2730, 37.8715]);
// [ -13611368.09..., 4561288.94... ]
```

To register every CRS at once:

```js
proj4.defs(
  Object.values(projCodes).map((crs) => [`${crs.auth_name}:${crs.code}`, crs.proj4string])
);
```

### Searching by name

```js
const utmZones = Object.values(projCodes).filter((crs) =>
  crs.name.startsWith('WGS 84 / UTM zone')
);
```

## Development

The dataset is generated from [pyproj](https://pyproj4.github.io/pyproj/) by
[generate.py](generate.py), which writes both `proj-codes.json` (the published
data, gitignored) and [proj-codes.csv](proj-codes.csv) (a browsable index).

Using [pixi](https://pixi.sh) to provide Python, Node, and pnpm:

```sh
pixi install
pixi run build
```

Or, with your own Python environment that has `pyproj` installed:

```sh
pnpm run build
```
