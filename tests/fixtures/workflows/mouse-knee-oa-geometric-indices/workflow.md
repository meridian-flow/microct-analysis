---
workflow_id: mouse-knee-oa-geometric-indices
modality: microct
species: mouse
anatomy: knee
study_type: OA geometric indices
description: Mouse knee OA geometric index workflow for distal femoral and tibial IIOC ratios.
stage_order:
  - intake
  - segmentation
  - seed-review
  - landmarks-orientation
  - roi
  - measurement
thresholds:
  bone_soft_tissue:
    value: 220
    unit: scanco
    meaning: bone vs soft tissue boundary
  subchondral_plate:
    value: 270
    unit: scanco
    meaning: subchondral plate and cortical bone
  segmentation_3d:
    value: 320
    unit: scanco
    meaning: 3D surface segmentation
  override_policy: user_may_override_with_rationale
landmarks:
  - name: intercondylar_groove_midpoint
    bone: femur
    anatomical_intent: upper midpoint of femoral groove line
    view: frontal
    fallback: midpoint of groove upper surface
  - name: intercondylar_notch
    bone: femur
    anatomical_intent: notch between femoral condyles
    view: frontal
    fallback: edge of notch entrance if eroded
  - name: lateral_condylar_edge
    bone: femur
    anatomical_intent: lateral extent of distal femur
    view: frontal
  - name: medial_condylar_edge
    bone: femur
    anatomical_intent: medial extent of distal femur
    view: frontal
  - name: tibial_plateau_midpoint
    bone: tibia
    anatomical_intent: center of proximal tibial surface
    view: frontal
  - name: epiphyseal_line
    bone: tibia
    anatomical_intent: growth plate boundary
    view: frontal
roi_definitions:
  - name: tibial_iioc
    bone: tibia
    superior_boundary: most_proximal_articular_surface
    inferior_boundary: most_proximal_growth_plate
    lateral_rule: full_width_at_growth_plate
    offset_um: 0
    note: articular surface to growth plate, all bone included
measurements:
  - name: distal_femoral_length
    kind: distance
    frame: oriented_frontal
    points: [intercondylar_groove_midpoint, intercondylar_notch]
    projection: sagittal_midplane
    unit: mm
  - name: distal_femoral_width
    kind: distance
    frame: oriented_frontal
    points: [lateral_condylar_edge, medial_condylar_edge]
    projection: frontal_plane
    unit: mm
  - name: distal_femoral_ratio
    kind: ratio
    numerator: distal_femoral_width
    denominator: distal_femoral_length
    unit: dimensionless
    acceptance:
      normal_range: [1.0, 1.28]
      oa_threshold: 1.245
  - name: tibial_iioc_height
    kind: slice_count
    frame: oriented_frontal
    boundaries: [most_proximal_articular_surface, most_proximal_growth_plate]
    slice_thickness_um: 10.5
    unit: mm
  - name: tibial_width
    kind: distance
    frame: oriented_frontal
    points: [medial_tibial_condyle_edge, lateral_tibial_condyle_edge]
    slice_selection: growth_plate_level_max_condyle_visibility
    unit: mm
  - name: tibial_iioc_ratio
    kind: ratio
    numerator: tibial_iioc_height
    denominator: tibial_width
    unit: dimensionless
    acceptance:
      normal_range: [0.28, 0.35]
      oa_threshold: 0.282
orientation_protocol:
  method: landmark_based_alignment
  target_plane: frontal
  anchor_landmarks: [intercondylar_groove_midpoint, intercondylar_notch]
  alignment_axis: long_axis_to_vertical
  tool: transform_editor_equivalent
  note: align tibia long axis to vertical, then rotate to frontal view for measurements
field_provenance:
  thresholds:
    source: paper
    confidence: high
    note: values from Tang et al. Table S1
  landmarks:
    source: paper
    confidence: high
  measurements:
    source: paper
    confidence: high
  roi_definitions:
    source: inferred
    confidence: medium
    note: exact offset interpretation inferred from methods text
acceptance_checks:
  segmentation:
    - check: bone_volume_ordering
      rule: femur > tibia > fibula > patella
      confidence_if_violated: low
    - check: condyle_separation
      rule: femoral condyles visually distinct
      confidence_if_violated: medium
  landmarks:
    - check: length_stable_reference
      rule: distal_femoral_length within 10% of prior accepted samples
      confidence_if_violated: medium
  roi:
    - check: growth_plate_visible
      rule: growth plate clearly identifiable in ROI view
      confidence_if_violated: low
  measurement:
    - check: ratio_sanity
      rule: distal_femoral_ratio between 0.8 and 2.5
      confidence_if_violated: low
reference_images:
  - path: ./references/segmentation-frontal-good.png
    stage: segmentation
    view: frontal
    purpose: compare condyle separation and osteophyte extent
    checks:
      - femoral condyles visually distinct
      - osteophyte extent visible at joint margins
  - path: ./references/landmarks-frontal.png
    stage: landmarks-orientation
    view: frontal
    purpose: verify landmark placement matches defined points
    checks:
      - groove midpoint and notch anchors visible
      - medial and lateral condylar edges bracket distal femur
sources:
  - citation: Tang et al. Geometric indices derived from uCT images (2026)
    locator: OA-uCT paper 251123.pdf
    doi: 10.3390/biology15030262
---

## Protocol identity
Mouse knee OA geometric indices — measures distal femoral width/length ratio and tibial IIOC height/width ratio as OA severity indicators.

## Scanner and acquisition
Scanco Medical VivaCT 40 cone-beam CT. 10.5 um isotropic voxels, 55 kVp, 145 uA, 300 ms integration time.

## Known pitfalls
- Sesamoid bones near joints misidentified as osteophytes
- ROI drift from growth plate if landmark placement is inconsistent
- Threshold 220 set for bone/soft tissue; changing it affects meniscus visibility
- Orientation correction required before tibial measurements
