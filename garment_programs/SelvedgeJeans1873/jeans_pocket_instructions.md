# Drafting the Pockets

Source: https://masterclasses.historical-tailoring.com/lesson/drafting-the-pockets-and-accessories/

> **Important:** Draft pockets only after you have completely fit your pattern
> with a muslin and transferred any alterations to your main pattern.

---

## Front Pocket

The front pocket is drafted directly onto the front leg draft, then traced to
separate sheets.

### A. Pocket Opening

1. Mark **point 0** at the top of the side seam at the waist. (All marks are
   on the seamline, not the seam allowance.)
2. Mark **3 1/4"** from point 0 along the side seam — lower edge of the pocket
   opening.
3. Mark **4 3/4"** along the waist from point 0 — top of the pocket opening.
4. Square out construction lines from both the waist and the side seam.
5. Draw a smooth **curve** connecting the two points.
6. Add **3/8" seam allowance** to the curved opening.

> For hip sizes above ~38", use Devere's graduated rulers to scale the pocket
> opening proportionally.

### B. Pocket Bag

7. Draw a line ~**1"** from the pocket opening (from the original lines, not
   the seam allowance), roughly parallel to the front fly.
8. Length: **10" to 12"**, depending on the rise.
9. Draw the lower bag line toward the side seam, **angling up slightly** (this
   keeps items balanced and prevents them falling out).
10. End the lower line ~**1 1/2"** from the side seam.
11. Connect the bag bottom to the side seam ~**2" below the pocket opening**
    with a curve.

### C. Pocket Facing

The facing is the visible band of fabric that shows when the pocket is open.
It is drafted on the front piece, then traced off as a separate cut piece.

12. Draw a line ~**1/2"** inside both the pocket opening and the pocket bag
    edge — this is the inner edge of the facing.
13. Extend the facing **1"–2"** below the pocket opening along the bag inner
    edge.
14. Draw the lower edge toward the side seam, meeting just above the top of
    the curved bag line (~**1 1/2"** below the pocket opening along the side
    seam).
15. The facing forms a closed shape: opening (offset) → side seam →
    lower curve → inner edge → back to opening top.

### D. 1873 Watch Pocket

A small standalone pocket positioned at the front waist, overlapping the
pocket opening area. This is a separate cut piece, not traced from the front.

**Shape:** pentagon / shield — straight top, straight sides, V-bottom.

16. Mark **point 0** at top center.
17. Top width: **1 3/4"** each side of center (**3 1/2"** total).
18. Straight sides for **4"** downward.
19. At 4", bottom width narrows to **1 1/2"** each side (**3"** total).
20. Below 4", sides taper inward to meet at a center point at **4 1/2"**
    total height — forming the V-bottom.

**Position on front:** Top falls at the waist line (center of waistband area);
bottom sits just below the front pocket opening.

### E. Seam Allowances

- Pocket bag: **3/8"** on bottom and curved edges; top and side get SA from
  the traced pattern. Remaining long edge is **cut on the fold**.
- Facing: **3/8"** on inside and lower edges.
- Watch pocket: **7/8"** on top (double fold for waistband), **3/8"** on
  sides and bottom.

### F. Standalone Cut Pieces

The watch pocket and facing are extracted as their own printable pattern pieces
(separate from the front pocket overlay):

- **Watch pocket** (`jeans_watch_pocket.py`): the pentagon/shield is rotated
  upright and re-origined to (0, 0) with SA applied (7/8" top, 3/8" sides and
  bottom). Grain line runs vertically through center.
- **Front pocket facing** (`jeans_front_facing.py`): the cutoff piece from
  the front panel between the waist (rise curve from pt1 to pocket_upper),
  the pocket opening curve, and the side seam (hip curve from pocket_lower
  back to pt1). Rotated 90° for layout. SA: 3/8" on waist and opening
  edges; 3/4" on side seam. Grain line vertical.

### G. Cut the Opening

When 100% satisfied, cut the pocket opening from the front leg along the seam
allowance line. Save the cutoff piece.

---

## Back Pocket

### Sizing

- For hip sizes up to ~38", use the given dimensions as-is.
- For larger sizes, use graduated rulers.
- Above ~46" hip, use your judgment — measure your wallet or hand size.
- **1873 jeans:** only one pocket (right side).
- **Modern jeans:** one on each side.

### Steps

1. Draw a vertical line from point 0.
2. Mark **7"** along the vertical (first reference mark).
3. Mark **8"** total length.
4. Mark the widths (~6" at mouth, tapering to ~4 1/2" at bottom from the 7"
   mark onward).
5. Draw the outline — straight sides down to 7", then angled inward to the
   narrower bottom.

### Seam Allowances

- Sides and bottom: **3/8"**
- Top: **7/8"** (accounts for double fold + denim thickness)

### Grain Line

- **Option 1 (recommended):** centerline as grainline, pocket mouth on
  crossgrain.
- **Option 2:** grainline along the side, better fabric match but opening
  prone to stretching.
