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
    attenuation_coefficient: 2.16  # cm^-1
  segmentation_3d:
    value: 320
    unit: scanco
    meaning: 3D surface segmentation
    attenuation_coefficient: 2.56  # cm^-1
  override_policy: user_may_override_with_rationale

landmarks:
  # --- Femoral landmarks: 3D surface points ---
  - name: intercondylar_groove_midpoint
    domain: femoral_3d_surface
    bone: femur
    anatomical_definition: >
      Superior midpoint of the patellar (trochlear) groove on the anterior
      distal femoral surface. The transition point where the femoral shaft
      meets the articular surface, at the top of the groove between the
      condyles.
    geometric_method: saddle_point
    geometric_params:
      surface_region: anterior_distal
      constraint: most_superior_groove_point
    view: frontal
    fallback:
      method: superior_anterior_midpoint
      description: most superior point of the anterior inter-condylar surface
      confidence: low
      requires_user_confirmation: true
      qc_check: femoral_length_must_be_2_0_to_2_6_mm
    paper_quote: "upper middle point of intercondylar groove"

  - name: intercondylar_notch
    domain: femoral_3d_surface
    bone: femur
    anatomical_definition: >
      Deepest point of the intercondylar fossa — the concavity between
      the medial and lateral condyles on the posterior/inferior aspect of
      the distal femur. The roof of the notch.
    geometric_method: notch_depth_maximum
    geometric_params:
      surface_region: posterior_intercondylar
      constraint: deepest_point_between_condyles
    view: frontal
    fallback:
      method: notch_entrance_edge
      description: edge of notch entrance if eroded
      confidence: low
      requires_user_confirmation: true
      qc_check: femoral_length_must_be_2_0_to_2_6_mm
    paper_quote: "the intercondylar notch"

  - name: lateral_condylar_edge
    domain: femoral_3d_surface
    bone: femur
    anatomical_definition: >
      Outermost lateral point of the distal femur on the frontal view,
      including any osteophyte outgrowths. Measures full transverse extent
      of bone (normal + pathological).
    geometric_method: surface_extreme
    geometric_params:
      direction: lateral
      plane: frontal
      z_range: condylar_region
      include_osteophytes: true
    view: frontal
    paper_quote: "edges of lateral condyle, representing osteophyte"

  - name: medial_condylar_edge
    domain: femoral_3d_surface
    bone: femur
    anatomical_definition: >
      Outermost medial point of the distal femur on the frontal view,
      including any osteophyte outgrowths.
    geometric_method: surface_extreme
    geometric_params:
      direction: medial
      plane: frontal
      z_range: condylar_region
      include_osteophytes: true
    view: frontal
    paper_quote: "edges of medial condyle, representing osteophyte"

  # --- Tibial landmarks: 2D oriented slice boundaries ---
  - name: articular_surface_proximal
    domain: tibial_2d_slice
    bone: tibia
    anatomical_definition: >
      The most proximal Z-slice where the tibial articular surface first
      appears. This is the superior boundary of the IIOC region.
    geometric_method: boundary_slice_scan
    geometric_params:
      scan_direction: superior_to_inferior
      detection: area_threshold
      source_volume: oriented_tibia_label_mask
      area_threshold_pct: 20  # of max per-slice tibia area in volume
      low_confidence_fallback: first_any_voxel
      requires_orientation: true
    paper_quote: "the most proximal appearance of the articular surface"

  - name: growth_plate_proximal
    domain: tibial_2d_slice
    bone: tibia
    anatomical_definition: >
      The most proximal Z-slice where the growth plate first appears
      when scanning from the articular surface distally. This is the
      inferior boundary of the IIOC region.
    geometric_method: boundary_slice_scan
    geometric_params:
      scan_direction: inferior_from_articular
      detection: bone_fill_ratio_drop
      source_volume: oriented_intensity_masked_by_label
      high_threshold: 270  # subchondral/trabecular bone
      low_threshold: 220   # bone/soft tissue
      fill_ratio_threshold_pct: 50  # ratio drops below this
      min_consecutive_above: 5  # slices above threshold before drop counts
      requires_orientation: true
    tie_breaking: >
      If boundary ambiguous (multiple candidates within 2 slices), use
      the more proximal candidate (conservative = smaller IIOC height).
    validation:
      oa6_1rk_expected_slice_count: 71
      oa6_1rk_roi_pos_z: 661
    paper_quote: "the most proximal appearance of the growth plate"

  - name: medial_tibial_condyle_edge
    domain: tibial_2d_slice
    bone: tibia
    anatomical_definition: >
      Medial-most border of the tibial bone on the measurement slice
      (growth plate level). On the oriented frontal cross-section.
    geometric_method: slice_bone_extent
    geometric_params:
      direction: medial
      requires_orientation: true
      measurement_slice_selection:
        method: max_bone_area
        search_region: iioc  # between articular_surface and growth_plate
        tie_threshold_voxels: 2  # slices within this area count tie
        tie_break: closest_to_growth_plate
        record_in_artifacts: true  # log selected slice index for QC
    paper_quote: "borders of medial tibial condyle"

  - name: lateral_tibial_condyle_edge
    domain: tibial_2d_slice
    bone: tibia
    anatomical_definition: >
      Lateral-most border of the tibial bone on the measurement slice
      (growth plate level). On the oriented frontal cross-section.
    geometric_method: slice_bone_extent
    geometric_params:
      direction: lateral
      requires_orientation: true
      measurement_slice_selection:
        method: max_bone_area
        search_region: iioc
        tie_threshold_voxels: 2
        tie_break: closest_to_growth_plate
        record_in_artifacts: true
    paper_quote: "borders of lateral tibial condyle"

roi_definitions:
  - name: tibial_iioc
    bone: tibia
    superior_boundary: articular_surface_proximal
    inferior_boundary: growth_plate_proximal
    lateral_rule: full_width_at_growth_plate
    offset_um: 0
    note: articular surface to growth plate, all bone included
    threshold: 270

  - name: medial_subchondral_trabecular
    bone: tibia
    compartment: medial
    description: >
      Medial compartment trabecular bone. Boundary with lateral compartment
      determined visually through center of proximal tibia. Includes all
      non-cortical bone. Growth plate excluded.
    threshold: 270
    contouring_method:
      source: amira_sop
      recipe: Cortical & Trabecular Isolation 8.13.21 FINALFINAL.hxrecipe
      steps:
        - morphological_closing: apply recipe to tibia binary label
        - shrink_interior: shrink × 3 (select inside, all slices, replace)
        - lock_exterior: freeze exterior voxels
        - threshold_classify: LB=1000-1500 → Material 2 (Subchondral bone); residual = Marrow
        - crop_growth_plate: ~20-25 slices at beginning of growth plates
        - total_bone: subchondral bone + marrow
      compartment_split: operator_visual_judgment  # no algorithmic rule
    scanco_reference:
      oa6_1rk_dims_voxels: [188, 132, 81]
      oa6_1rk_dims_mm: [1.974, 1.386, 0.851]

  - name: lateral_subchondral_trabecular
    bone: tibia
    compartment: lateral
    description: >
      Lateral compartment trabecular bone. Same rules as medial.
    threshold: 270
    contouring_method:
      source: amira_sop
      recipe: Cortical & Trabecular Isolation 8.13.21 FINALFINAL.hxrecipe
      steps:
        - morphological_closing: apply recipe to tibia binary label
        - shrink_interior: shrink × 3 (select inside, all slices, replace)
        - lock_exterior: freeze exterior voxels
        - threshold_classify: LB=1000-1500 → Material 2 (Subchondral bone); residual = Marrow
        - crop_growth_plate: ~20-25 slices at beginning of growth plates
        - total_bone: subchondral bone + marrow
      compartment_split: operator_visual_judgment  # no algorithmic rule
    scanco_reference:
      oa6_1rk_dims_voxels: [208, 180, 102]
      oa6_1rk_dims_mm: [2.184, 1.890, 1.071]

  - name: medial_subchondral_plate
    bone: tibia
    compartment: medial
    description: Thin cortical layer beneath medial articular cartilage.
    threshold: 270
    contouring_method:
      source: amira_sop
      note: >
        Derived from the cropped growth plate segmentation. The subchondral
        plate is the thin high-density cortical layer at the articular surface,
        separated from trabecular bone by the SOP's closing + threshold procedure.
      compartment_split: operator_visual_judgment
    scanco_reference:
      oa6_1rk_dims_voxels: [200, 152, 18]

  - name: lateral_subchondral_plate
    bone: tibia
    compartment: lateral
    description: Thin cortical layer beneath lateral articular cartilage.
    threshold: 270
    contouring_method:
      source: amira_sop
      note: >
        Same procedure as medial subchondral plate. Lateral compartment.
      compartment_split: operator_visual_judgment
    scanco_reference:
      oa6_1rk_dims_voxels: [132, 144, 16]

measurements:
  # --- Femoral domain: 3D surface measurements ---
  - name: distal_femoral_length
    domain: femoral_3d_surface
    kind: surface_distance
    method: euclidean_3d
    points: [intercondylar_groove_midpoint, intercondylar_notch]
    unit: mm
    paper_definition: >
      Straight-line distance between upper middle point of intercondylar
      groove and the intercondylar notch, measured with Ruler tool on 3D model.
    clinical_note: >
      Stable reference parameter — remains unchanged after MMS at 4 and 8 weeks.
      Used as denominator for width/length ratio.
    acceptance:
      oa6_1rk_published: 2.29
      normal_range: [2.18, 2.49]
      mms_8wk_range: [2.26, 2.49]
      tolerance_pct: 10

  - name: distal_femoral_width
    domain: femoral_3d_surface
    kind: surface_distance
    method: frontal_projected
    points: [lateral_condylar_edge, medial_condylar_edge]
    unit: mm
    paper_definition: >
      Distance between edges of lateral and medial condyle, representing
      osteophyte formation. Measured on front view of µCT images.
    acceptance:
      oa6_1rk_published: 3.48
      normal_range: [2.70, 2.98]
      mms_8wk_range: [3.13, 3.58]
      tolerance_pct: 10

  - name: distal_femoral_ratio
    domain: derived
    kind: ratio
    numerator: distal_femoral_width
    denominator: distal_femoral_length
    unit: dimensionless
    paper_definition: >
      Width-to-length ratio. Below 1.28 in all normal joints (11/12 below
      1.25). Above 1.30 in all OA joints. Key OA severity indicator.
    acceptance:
      oa6_1rk_published: 1.520
      oa6_1rk_second_reader: 1.404
      normal_threshold: 1.28
      oa_threshold: 1.30
      normal_range: [1.116, 1.239]
      mms_8wk_range: [1.365, 1.520]
      tolerance_pct: 10

  # --- Tibial domain: 2D oriented slice measurements ---
  - name: tibial_iioc_height
    domain: tibial_2d_slice
    kind: boundary_slice_count
    method: boundary_slice_count
    boundaries: [articular_surface_proximal, growth_plate_proximal]
    slice_thickness_mm: 0.0105
    unit: mm
    paper_definition: >
      Maximum height between growth plate and tibia articular surface,
      calculated by counting µCT slices between the most proximal appearance
      of the articular surface and the most proximal appearance of the growth
      plate. Each slice is 10.5 µm.
    verification: >
      Cross-checked against Table S1: OA6-1RK BV-ArtSurf-GrowthPlate ROI
      Dim-Z = 71 slices. 71 × 0.0105 = 0.7455 mm = Table S3 value.
    acceptance:
      oa6_1rk_published: 0.7455
      oa6_1rk_slice_count: 71
      normal_range: [0.777, 0.872]
      mms_8wk_range: [0.672, 0.819]
      tolerance_slices: 3

  - name: tibial_width
    domain: tibial_2d_slice
    kind: slice_distance
    method: bone_extent_on_slice
    points: [medial_tibial_condyle_edge, lateral_tibial_condyle_edge]
    measurement_slice: growth_plate_level
    requires_orientation: true
    unit: mm
    paper_definition: >
      Straight-line distance between the borders of medial and lateral
      tibial condyle, measured at the level of the growth plate on
      oriented frontal ortho slice.
    acceptance:
      oa6_1rk_published: 2.95
      normal_range: [2.51, 2.81]
      mms_8wk_range: [2.83, 3.27]
      tolerance_pct: 10

  - name: tibial_iioc_ratio
    domain: derived
    kind: ratio
    numerator: tibial_iioc_height
    denominator: tibial_width
    unit: dimensionless
    paper_definition: >
      Ratio of IIOC height to tibial width. Sensitive OA indicator.
      Decreases in OA due to subchondral collapse (reduced height) and
      osteophyte formation (increased width).
    acceptance:
      oa6_1rk_published: 0.253
      oa6_1rk_second_reader: 0.232
      normal_range: [0.289, 0.318]
      mms_8wk_range: [0.206, 0.275]
      tolerance_pct: 10

  # --- Trabecular morphometry (per-compartment) ---
  - name: medial_trabecular_morphometry
    domain: trabecular_roi
    kind: roi_stat
    roi: medial_subchondral_trabecular
    threshold: 270
    algorithm: distance_transform
    metrics: [BV/TV, Tb.Th, Tb.N, Tb.Sp, TV, BV]
    unit: mixed
    acceptance:
      oa6_1rk_bv_tv: 0.1193
      oa6_1rk_tb_th_mm: 0.0623
      oa6_1rk_tb_n_per_mm: 2.8949
      oa6_1rk_tb_sp_mm: 0.3750
      oa6_1rk_tv_mm3: 0.3800
      oa6_1rk_bv_mm3: 0.0453

  - name: lateral_trabecular_morphometry
    domain: trabecular_roi
    kind: roi_stat
    roi: lateral_subchondral_trabecular
    threshold: 270
    algorithm: distance_transform
    metrics: [BV/TV, Tb.Th, Tb.N, Tb.Sp, TV, BV]
    unit: mixed
    acceptance:
      oa6_1rk_bv_tv: 0.2604
      oa6_1rk_tb_th_mm: 0.0859
      oa6_1rk_tb_n_per_mm: 4.0346
      oa6_1rk_tb_sp_mm: 0.2617
      oa6_1rk_tv_mm3: 0.7529
      oa6_1rk_bv_mm3: 0.1961

  - name: total_iioc_bone_volume
    domain: trabecular_roi
    kind: roi_stat
    roi: tibial_iioc
    threshold: 270
    metrics: [BV/TV, TV, BV]
    unit: mixed
    acceptance:
      oa6_1rk_bv_tv: 0.4005
      oa6_1rk_tv_mm3: 5.4729
      oa6_1rk_bv_mm3: 2.1919

orientation_protocol:
  method: pca_tibia_alignment
  target_plane: frontal
  source_label: tibia
  algorithm:
    step_1: >
      Extract tibia principal axes via PCA on thresholded voxel positions.
      First principal component = long axis.
    step_2: >
      Rotate long axis (PC1) to align with Z-axis (superior-inferior).
    step_3: >
      Align second principal component (widest cross-section = ML axis)
      to X-axis to establish frontal orientation.
    step_4: >
      Apply rigid rotation to both the tibia label mask (nearest-neighbor
      interpolation, order=0) and the original intensity volume (linear
      interpolation). Center result on volume midpoint.
  resampling:
    label_mask: nearest_neighbor  # order=0 — preserves discrete labels
    intensity_volume: linear      # needed for growth plate 270/220 ratio
  design_status: extrapolation
  design_note: >
    The paper uses manual Transform Editor alignment (operator visual
    judgment). This PCA-based algorithm is our engineering approximation,
    NOT paper-ground-truth. Requires validation against Table S2 values.
  validation:
    sample: OA6-1RK
    table_s2_offsets: {x: -2.9505, y: -7.91175, z: -131.3195}
    success_criterion: >
      Oriented tibia produces IIOC height = 71 ± 3 slices and
      tibial width = 2.95 ± 0.30 mm.
  fallback: user_assisted_orientation
  fallback_note: >
    If PCA-based alignment produces measurements outside acceptance
    tolerance, display the oriented tibia in PyVista and ask the user
    to confirm or adjust frontal alignment.
  dependency: >
    Tibial orientation must be applied before any tibial 2D slice
    measurements. Femoral 3D surface measurements are independent
    of tibial orientation.

field_provenance:
  thresholds:
    source: paper
    confidence: high
    note: values from Tang et al. methods section
  landmarks:
    source: paper
    confidence: high
    note: >
      Anatomical definitions extracted from methods and discussion text.
      Geometric methods are implementation-level design.
  measurements:
    source: paper
    confidence: high
    note: >
      Acceptance values extracted from supplementary Table S3 (OA6-1RK).
      Ranges computed from all samples in S3.
  roi_definitions:
    source: paper_and_supplementary
    confidence: high
    note: >
      ROI dimensions verified against Table S1 SCANCO measurements.
      Trabecular ROI Dim-Z confirmed to match IIOC height.
  trabecular_morphometry:
    source: supplementary_table_s1
    confidence: high
    note: >
      Reference values from SCANCO evaluation software V6.5. DT (distance
      transform) method used for Tb.Th, Tb.N, Tb.Sp. VOX (voxel counting)
      used for BV/TV, TV, BV.

acceptance_checks:
  segmentation:
    - check: bone_volume_ordering
      rule: femur > tibia > fibula > patella
      confidence_if_violated: low
    - check: condyle_separation
      rule: femoral condyles visually distinct
      confidence_if_violated: medium
  landmarks:
    - check: femoral_length_stability
      rule: >
        distal_femoral_length between 2.0 and 2.6 mm. If prior samples
        exist, within 10% of their mean. Femoral length is the stable
        reference parameter — it should NOT change with OA severity.
      confidence_if_violated: medium
    - check: groove_notch_anatomy
      rule: >
        groove midpoint must be superior to notch. Distance between them
        should be 2.0-2.6 mm, not 3+ mm (which indicates shaft extent
        was measured instead of the distal surface landmarks).
      confidence_if_violated: low
  roi:
    - check: growth_plate_visible
      rule: growth plate clearly identifiable in ROI view
      confidence_if_violated: low
    - check: iioc_slice_count_plausible
      rule: >
        IIOC slice count between 50 and 100 (0.525 - 1.050 mm). Values
        outside this range suggest boundary misidentification.
      confidence_if_violated: low
  measurement:
    - check: femoral_ratio_sanity
      rule: distal_femoral_ratio between 0.9 and 2.0
      confidence_if_violated: low
    - check: iioc_is_slice_multiple
      rule: >
        tibial_iioc_height must be an exact multiple of slice thickness
        (0.0105 mm). Non-integer slice counts indicate a computation error.
      confidence_if_violated: low
    - check: tibial_ratio_sanity
      rule: tibial_iioc_ratio between 0.15 and 0.45
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
    purpose: verify landmark placement matches defined anatomical features
    checks:
      - groove midpoint at superior end of patellar groove, not at femur bbox top
      - notch at deepest point of intercondylar fossa, not at femur bbox bottom
      - condylar edges at outermost bone extent including osteophytes
  - path: ./references/tibial-oriented-slice.png
    stage: roi
    view: oriented_frontal_slice
    purpose: verify orientation correction and IIOC boundary identification
    checks:
      - tibia long axis aligned vertical
      - articular surface and growth plate boundaries clearly identifiable
      - medial and lateral condyle borders visible

sources:
  - citation: Tang et al. Geometric indices derived from uCT images (2026)
    locator: OA-uCT paper 251123.pdf
    doi: 10.3390/biology15030262
  - citation: Supplementary Table S1 (SCANCO measurements)
    locator: exp_out/biology-15-00262-s001/Supplemental Table S1, uCT reported 00Results.xlsx
  - citation: Supplementary Table S2 (tibia rotation correction)
    locator: exp_out/biology-15-00262-s001/Supplemental Table S2, tibia rotation correction.xlsx
  - citation: Supplementary Table S3 (geometric indices, all samples)
    locator: exp_out/biology-15-00262-s001/Supplemental Table S3, Mint OA 6-7-8 uCT combined 1-6-26.xlsx
---

## Protocol identity
Mouse knee OA geometric indices — measures distal femoral width/length ratio and tibial IIOC height/width ratio as OA severity indicators. From Tang et al. (Biology 15(3):262).

## Scanner and acquisition
Scanco Medical VivaCT 40 cone-beam CT. 10.5 µm isotropic (cubical) voxels, 55 kVp, 145 µA, 300 ms integration time. Threshold 220 distinguishes bone from soft tissue.

## Measurement methodology

### Femoral measurements (3D surface)
Femoral geometric parameters are measured using the interactive Ruler tool in Amira on the 3D rendered model. The operator places the ruler endpoints on specific anatomical surface points — NOT on bounding box corners or label centroids.

- **Distal femoral length**: upper midpoint of intercondylar groove → intercondylar notch
- **Distal femoral width**: lateral condylar edge → medial condylar edge (includes osteophytes)

### Tibial measurements (2D oriented slices)
Tibial measurements require orientation correction first. The µCT dataset is transformed using the Transform Editor to align the tibia parallel to x/y plane. Ortho Slice generates frontal sections. Measurements are then taken on specific slices.

- **IIOC height**: count µCT slices from most proximal articular surface to most proximal growth plate. Multiply by 10.5 µm. This is a discrete slice count, not a continuous distance.
- **Tibial width**: distance between medial and lateral tibial condyle borders on the oriented frontal slice at growth plate level.

## Inter-reader variability
Table S3 includes measurements from two readers (Mint and Leah). For OA6-1RK:
- Femoral ratio: 1.520 (Mint) vs 1.404 (Leah) — 8% difference
- IIOC ratio: 0.253 (Mint) vs 0.232 (Leah) — 9% difference

This sets the floor for pipeline accuracy: ±10% of published values represents inter-operator agreement.

## OA6-1RK reference values (acceptance test)

| Measurement | Published value | Unit |
| --- | --- | --- |
| Distal femur length | 2.29 | mm |
| Femur width | 3.48 | mm |
| Width/length ratio | 1.520 | dimensionless |
| Tibia plate width | 2.95 | mm |
| Max Height II-OC | 0.7455 (71 slices) | mm |
| Plate H/W ratio | 0.253 | dimensionless |
| Medial BV/TV | 0.1193 | dimensionless |
| Medial Tb.Th | 0.0623 | mm |
| Medial Tb.N | 2.8949 | 1/mm |
| Medial Tb.Sp | 0.3750 | mm |

## Known pitfalls
- Sesamoid bones near joints misidentified as osteophytes
- ROI drift from growth plate if landmark placement is inconsistent
- Threshold 220 set for bone/soft tissue; changing it affects meniscus visibility
- Orientation correction required before tibial measurements
- Femoral length must NOT be measured as label Z-extent (produces ~3.4mm, 50% too high)
- Condylar edges must include osteophytes (the width metric deliberately captures pathological bone)
- IIOC height must be an integer slice count — non-integer results indicate an error
- Medial/lateral compartment split is an operator judgment, not an algorithmic rule
