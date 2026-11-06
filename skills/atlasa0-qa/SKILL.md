---
name: atlasa0-qa
description: Check and calibrate AtlasA0 after any code change - run the offline tests, the calibration table, a dry run, and (when internet exists) the live tests.
---
Author: Imaad Ullah Khan Yameen  
Email: yameenimaad@gmail.com  
*This code is not for sale*

# AtlasA0 QA

## Tools
`pytest` (offline, about 110 tests) | `python tools/calibrate.py` (A0 pixels, scale bars, marker sizes, tile zoom, map fill, TIFF pixel check) | `python -m atlasa0 ... --dry-run` | `ATLASA0_LIVE=1 pytest tests/test_live.py -v -s`

## Local variables
`ATLASA0_LIVE=1` turns live tests on (needs osmnx, geopandas, shapely, internet). Without those libraries, tests use stand-ins and live tests skip.

## Procedure
1. Edit code and tests together; layout numbers live in `config.AXES_RECT` and `furniture.py`/`render.py` helpers.
2. Run `pytest`; all must pass.
3. Run `tools/calibrate.py`; axes fill must read 100% and GeoTIFF pixels square.
4. Dry-run a mixed job list.
5. Report exactly what ran: offline-only results are NOT proof that live downloads or drawing work.
