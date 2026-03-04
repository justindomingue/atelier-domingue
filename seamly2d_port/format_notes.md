# Seamly2D File Format Reference

Reference for generating .sm2d pattern files and .smis measurement files
programmatically from the Atelier Domingue drafting pipeline.

## File types

| Extension | Purpose | Old (Valentina) equivalent |
|-----------|---------|---------------------------|
| `.sm2d`   | Pattern design file | `.val` |
| `.smis`   | Individual-size measurements | `.vit` |
| `.smms`   | Multi-size measurements | `.vst` |

Seamly2D CLI can still open `.val`/`.vit` files and will auto-convert them.

## CLI usage (headless export)

```bash
export QT_QPA_PLATFORM=offscreen

# SVG export (format 0)
seamly2d -b <basename> -d <output_dir> -m <measurements.smis> -f 0 <pattern.sm2d>

# Full-size PDF (format 1)
seamly2d -b <basename> -d <output_dir> -m <measurements.smis> -f 1 <pattern.sm2d>

# Tiled PDF for home printing (format 2)
seamly2d -b <basename> -d <output_dir> -m <measurements.smis> -f 2 <pattern.sm2d>

# DXF export (format 14 = DXF 2000)
seamly2d -b <basename> -d <output_dir> -m <measurements.smis> -f 14 <pattern.sm2d>
```

Key flags:
- `-b` basename: enables console/export mode (required for headless export)
- `-d` destination: output folder
- `-m` mfile: measurement file override
- `-f` format: output format number
- `-W` paper width, `-H` paper height (for tiled output)
- `-l` layout units: `cm`, `mm`, `inch`
- `-G` gap width: spacing between pieces in layout

## .smis measurement file format (v0.3.4)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<smis>
    <version>0.3.4</version>
    <read-only>false</read-only>
    <notes/>
    <unit>cm</unit>
    <pm_system>998</pm_system>
    <personal>
        <family-name/>
        <given-name/>
        <birth-date>1800-01-01</birth-date>
        <gender>unknown</gender>
        <email/>
    </personal>
    <body-measurements>
        <m name="waist_circ" value="86.36"/>
        <m name="hip_circ" value="101.6"/>
    </body-measurements>
</smis>
```

Measurement values are always in the unit specified by `<unit>`.
Values can be numeric literals or formulas referencing other measurements:
```xml
<m name="neck_arc_b" value="(neck_circ - neck_arc_f)"/>
```

## .sm2d pattern file format (v0.6.0)

Top-level structure:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<pattern>
    <version>0.6.0</version>
    <unit>cm</unit>
    <description/>
    <notes/>
    <measurements>path/to/measurements.smis</measurements>
    <increments/>
    <draw name="PieceName">
        <calculation>  <!-- drafting geometry -->
        </calculation>
        <modeling>      <!-- references for detail pieces -->
        </modeling>
        <details>       <!-- pattern piece outlines -->
        </details>
    </draw>
</pattern>
```

### Calculation elements (drafting geometry)

#### Points

Every point requires `id` (unique unsigned int), `name` (label), `mx`/`my`
(label offset), and `type`.

**Single point** (absolute position):
```xml
<point id="1" type="single" name="A" x="10" y="10" mx="0.13" my="0.26"/>
```

**End-of-line point** (from base point at angle+length):
```xml
<point id="2" type="endLine" name="B" basePoint="1" angle="0" length="20"
       typeLine="hair" lineColor="black" mx="0.13" my="0.26"/>
```

**Along-line point** (fraction/distance along a line between two points):
```xml
<point id="3" type="alongLine" name="C" firstPoint="1" secondPoint="2"
       length="10" typeLine="hair" lineColor="black" mx="0.13" my="0.26"/>
```

**Point at line intersection**:
```xml
<point id="5" type="lineIntersect" name="E"
       p1Line1="1" p2Line1="2" p1Line2="3" p2Line2="4" mx="0.13" my="0.26"/>
```

**Point on curve** (at a distance along a spline):
```xml
<point id="6" type="cutSpline" name="F" spline="10" length="15"
       mx="0.13" my="0.26"/>
```

`typeLine` values: `none`, `hair`, `dashLine`, `dotLine`, `dashDotLine`, `dashDotDotLine`
`lineColor` values: `black`, `green`, `blue`, `darkRed`, `darkGreen`, `darkBlue`, `yellow`, `lightsalmon`, `goldenrod`, `orange`, `deeppink`, `violet`, `darkviolet`, `mediumseagreen`, `lime`, `deepskyblue`, `cornflowerblue`

#### Lines

```xml
<line id="5" firstPoint="1" secondPoint="4" typeLine="hair" lineColor="black"/>
```

#### Splines (Bézier curves)

**Simple cubic spline** (two endpoints, two control angles+lengths):
```xml
<spline id="10" type="simpleInteractive" point1="1" point4="2"
        angle1="45" length1="5" angle2="225" length2="5"
        color="black" penStyle="hair"/>
```
- `point1`, `point4`: start and end point IDs
- `angle1`, `length1`: outgoing tangent angle and length at start
- `angle2`, `length2`: incoming tangent angle and length at end

**Spline path** (multi-point spline through several points):
```xml
<spline id="11" type="pathInteractive" color="black" penStyle="hair">
    <pathPoint pSpline="1" angle1="0" length1="3" angle2="180" length2="3"/>
    <pathPoint pSpline="2" angle1="0" length1="3" angle2="180" length2="3"/>
    <pathPoint pSpline="3" angle1="0" length1="3" angle2="180" length2="3"/>
</spline>
```

`penStyle` for curves: `hair`, `dashLine`, `dotLine`, `dashDotLine`, `dashDotDotLine`

### Modeling section

Each calculation object used in a detail piece needs a modeling reference:
```xml
<modeling>
    <point id="100" idObject="1" inUse="true" type="modeling"/>
    <spline id="101" idObject="10" inUse="true" type="modeling"/>
</modeling>
```

### Details section (pattern pieces)

```xml
<detail id="200" name="Front Panel" closed="1" inLayout="true"
        seamAllowance="true" width="1" forbidFlipping="false" mx="0" my="0">
    <data letter="" visible="false" fontSize="0" mx="0" my="0"
          width="1" height="1" rotation="0" onFold="false"
          annotation="" orientation="" rotationWay="" tilt="" foldPosition=""/>
    <patternInfo visible="false" fontSize="0" mx="0" my="0"
                 width="1" height="1" rotation="0"/>
    <grainline visible="true" arrows="0" length="10" mx="0" my="0" rotation="90"/>
    <nodes>
        <node idObject="100" type="NodePoint"/>
        <node idObject="101" type="NodeSpline"/>
        <node idObject="102" type="NodePoint"/>
    </nodes>
</detail>
```

Node types: `NodePoint`, `NodeSpline`, `NodeSplinePath`, `NodeArc`

Per-node seam allowance can be set via:
```xml
<node idObject="100" type="NodePoint" before="1.5" after="0.5"/>
```
- `before`: SA width before this node (toward previous edge)
- `after`: SA width after this node (toward next edge)

## Mapping: Atelier Domingue primitives → Seamly2D

| Atelier Domingue | Seamly2D equivalent |
|------------------|---------------------|
| `np.array([x, y])` absolute point | `<point type="single" x="x" y="y"/>` |
| Point at angle+distance from base | `<point type="endLine" basePoint="id" angle="a" length="d"/>` |
| Point along a line segment | `<point type="alongLine" firstPoint="id1" secondPoint="id2" length="d"/>` |
| `_bezier_cubic(P0, P1, P2, P3)` | `<spline type="simpleInteractive" point1="id1" point4="id2" angle1="a1" length1="l1" angle2="a2" length2="l2"/>` |
| `_bezier_quad(P0, P1, P2)` | Convert to cubic: P1'=P0+2/3*(P1-P0), P2'=P2+2/3*(P1-P2), then use simpleInteractive |
| `offset_polyline` / seam allowance | `detail seamAllowance="true" width="w"` + per-node `before`/`after` |
| Notch at point on edge | `<node ... passmark="true" passmarkLine="one"/>` |
| Grainline | `<grainline visible="true" rotation="r" length="l"/>` |
| Internal reference line | `<line typeLine="dashLine"/>` in calculation (visible but not part of detail piece) |
| Measurement `m["waist"]` | `waist_circ` in formula expressions |

### Converting Bézier control points to Seamly2D angles/lengths

Seamly2D defines cubic splines via tangent angles and lengths at each endpoint,
not via explicit control points. The conversion is:

```python
import numpy as np

def control_points_to_seamly(P0, CP1, CP2, P3):
    """Convert cubic Bézier control points to Seamly2D angle/length format."""
    # Outgoing tangent at P0
    d1 = CP1 - P0
    angle1 = np.degrees(np.arctan2(-d1[1], d1[0]))  # Y-axis inverted in Seamly2D
    length1 = np.linalg.norm(d1)

    # Incoming tangent at P3
    d2 = CP2 - P3
    angle2 = np.degrees(np.arctan2(-d2[1], d2[0]))  # Y-axis inverted
    length2 = np.linalg.norm(d2)

    return angle1, length1, angle2, length2
```

Note: Seamly2D uses screen coordinates (Y increases downward), which matches
the Atelier Domingue convention if the pattern is drafted with Y pointing down.

## Measurement name mapping

| Atelier Domingue YAML | Seamly2D standard name |
|------------------------|------------------------|
| `waist` | `waist_circ` |
| `seat` | `hip_circ` |
| `inseam` | `leg_crotch_to_floor` |
| `side_length` | `leg_waist_side_to_floor` |
| `waistband_width` | (custom increment) |
| `hem_width` | (custom increment) |
| `knee_width` | (custom increment) |

Custom measurements not in Seamly2D's standard set must be defined as
`<increments>` in the pattern file:
```xml
<increments>
    <increment name="#waistband_width" formula="3.81"/>
    <increment name="#hem_width" formula="45.72"/>
    <increment name="#knee_width" formula="50.8"/>
</increments>
```
Custom increment names are prefixed with `#` in formulas.
