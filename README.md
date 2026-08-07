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