# CHOWNET Nigerian Food Concept Registry

This directory contains a reproducible pilot ontology derived from the 172
labels configured in CHOWNET-V1. It is a **concept registry**, not a validated
food-composition table and not a complete dietary-assessment ontology.

## Files

- `schema.json`: machine-readable definition of a registry record.
- `chownet_label_mappings.csv`: one row per original CHOWNET class ID.
- `food_concepts.csv`: one row per normalized food concept.
- `food_ontology.json`: concepts, label mappings, hierarchy, provenance, and
  generation statistics in one document.
- `review_queue.csv`: mappings requiring curator or nutrition-expert review.
- `validation_report.json`: reproducible integrity and annotation checks.
- `build_ontology.py`: dependency-free generator and validator.
- `CHOWNET_Nutritionist_Review.xlsx`: formatted expert-curation workbook with
  an initial 30-food batch, source-image links, dropdowns, and review templates.
- `build_review_workbook.py`: reproducibly generates the Excel workbook (uses
  `openpyxl`).

Generated artifacts are committed so they can be reviewed without running
code. Rebuild them from the repository root with:

```powershell
python data/ontology/build_ontology.py
python data/ontology/build_review_workbook.py
```

The workbook generator requires `openpyxl`.

The script reads `experiments/object_detection/yolov8/notes.json`, which is
treated as the authoritative class-ID source. It also counts actual YOLO
annotations in the training and validation directories.

## Interpretation rules

- `exact_synonym` is reserved for spelling, punctuation, whitespace, or number
  variants that do not change the intended food concept.
- `unresolved` is used when the label is too vague or internally ambiguous.
- Scientific names are supplied only for unambiguous primary ingredients and
  remain candidate assertions until expert review.
- External ontology and food-composition IDs are deliberately blank. They must
  be supported by a cited source and reviewed before use.
- Nutrient inference must not be performed directly from the hierarchy. A
  reviewed food-composition mapping, recipe/ingredient representation, portion,
  and preparation state are required.

## Review workflow

1. Review `review_queue.csv`, prioritizing observed labels with high annotation
   counts.
2. Confirm whether each entry represents a food, ingredient, preparation,
   composite dish, or unusably broad detector label.
3. Add evidence-backed external identifiers and record the source/version.
4. Link variable dishes to recipes or multiple composition records rather than
   forcing a single nutrient profile.
5. Change `review_status` only after documented curator or expert review.

## Scope and limitations

This first version is Nigerian and CHOWNET-specific. “LMIC” is not modeled as a
cuisine or ontology class. Expansion should happen country by country while
reusing the same schema. Regional dishes that resemble one another should be
linked as related concepts, not automatically collapsed into synonyms.

## Registry summary

The validation report records 172 source labels mapped to 154 normalized concepts,
98 represented classes, and 432 boxes (312 training, 120 validation). There are
49 high-priority and 48 medium-priority review records. One box width is flagged
for floating-point rounding above 1 (1.0000000000000002). No duplicate concept IDs
or orphan mappings are reported. Structural checks do not validate food semantics
or nutrient values.
