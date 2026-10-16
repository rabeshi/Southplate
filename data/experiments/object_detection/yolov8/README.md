# CHOWNET-V1 YOLOv8 food detection experiment

This pilot fine-tunes a pretrained Ultralytics YOLOv8n detector to locate and
classify Nigerian foods. Training uses 94 images and validation uses 24 images,
with corresponding YOLO bounding-box labels under `train/food` and `valid/food`.
The annotations contain 432 boxes (312 training, 120 validation).

## Class vocabulary

`notes.json` defines original class IDs and `data.yaml` configures 172 classes.
The dataset README reports 99 unique labels, while the ontology validator finds
98 class IDs represented in the committed annotations. These counts refer to
different artifacts and should not be treated as interchangeable.

## Training and results

`train.py` loads `yolov8n.pt`, requests 1,000 epochs with augmentation, and then
runs validation. Saved `runs/detect/train11/args.yaml` records image size 640,
batch size 16, seed 0, and early-stopping patience 100. The archived CSV ends at
epoch 567; the requested epoch limit does not imply all epochs completed.

Final-row validation metrics: precision 0.67084, recall 0.31541, mAP@0.5 0.38426,
and mAP@0.5:0.95 0.27447. These are not independently verified best-checkpoint
or held-out test results. The small validation set limits generalization claims.

`runs/detect/train11` includes metric history, precision-recall curves, confusion
matrices, prediction previews, and best/last weights. `runs/detect/train102`
contains additional plots without a complete training history here.
`best_aug.pt` and `yolov8n.pt` are also included.

## Running a new experiment

Install `ultralytics` in your Python environment. From this folder, resolve the
train/val entries in `data.yaml` to this checkout's `train/food/images` and
`valid/food/images`, then run:

```bash
yolo detect train model=yolov8n.pt data=data.yaml epochs=1000 augment=True imgsz=640 batch=16 seed=0 patience=100
```

The original training/inference scripts retain author-specific paths that must
be updated. No dependency lockfile or original environment is supplied, so exact
numerical reproduction is not guaranteed.
