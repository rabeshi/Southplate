# SouthPlate

SouthPlate is a static website built with HTML, JavaScript, and image assets.

## Run locally

From the project directory, start a local web server:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000/SouthPlate.dc.html
```

## Project structure

- `SouthPlate.dc.html` — main website page
- `support.js` — client-side behavior
- `uploads/` — website image assets
- `vercel.json` — maps the site root to the main page on Vercel

## Deploy

The project is configured for deployment as a static site on Vercel. The root URL is rewritten to `SouthPlate.dc.html`.

## Dataset, experiment, and ontology

- [CHOWNET-V1](data/README.md): 118 annotated Nigerian food images, with 99 unique
  labels reported in the dataset documentation. [Download on Zenodo](https://zenodo.org/records/13633554).
- [YOLOv8 experiment](data/experiments/object_detection/yolov8/README.md): food
  detection using 94 training and 24 validation images, with annotations,
  checkpoints, and archived evaluation results.
- [Food concept registry](data/ontology/README.md): a pilot ontology mapping 172
  configured labels to 154 normalized concepts, with provenance, validation,
  a review queue, and an expert-review workbook. Expert review and evidence-backed
  food-composition mappings are required before nutrient estimation.
