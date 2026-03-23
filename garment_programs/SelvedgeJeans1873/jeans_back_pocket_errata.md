# Pattern Text Errata

Errors and ambiguities found in the "Drafting the Pockets and Accessories" lesson from Historical Tailoring Masterclasses.

## 1. Back pocket depth marks — text/diagram conflict

**Section:** Back Pocket

**Text says:** "measuring off 7″ and 8″ for the total length"

**Diagram shows:** The centerline marks in `back-pocket-1-3-1024x1017.png` are labeled at **6″** (narrowing) and **7″** (bottom point).

**Problem:** The text is off by 1″ on both marks. The diagram is correct.

**Our code:** follows the diagram — `mid_depth = 6.0*INCH`, `total_depth = 7.0*INCH` (`jeans_back_pocket.py:74-75`).

**Sanity check:** 7″ total depth is already generous for vintage jeans back pockets (typical ~6–6.5″); 8″ would be oversized.
