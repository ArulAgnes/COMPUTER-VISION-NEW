"""Data-centric closed-loop computer vision platform — AI package.

Modules by pipeline stage:

- ``dataset``     dataset discovery, splitting, versioning   (Stages 2, 4, 5+)
- ``annotation``  annotation storage and validation          (Stage 3)
- ``augmentation`` train-only augmentation                   (Stage 5)
- ``model``       custom detector, random initialization     (Stage 6)
- ``training``    from-scratch training engine               (Stage 7)
- ``evaluation``  IoU / precision / recall / F1 / mAP        (Stage 8)
- ``diagnostics`` error analysis, data diagnosis,            (Stage 9)
                  recommendations
- ``inference``   image and camera inference                 (Stage 10)
"""
