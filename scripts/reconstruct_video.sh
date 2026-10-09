#!/usr/bin/env bash
# Video -> frames -> COLMAP sparse 3-D model (CPU only; works on a Mac without CUDA).
#
# Usage: scripts/reconstruct_video.sh VIDEO START_SEC DURATION_SEC WORK_DIR [FPS]
# Example (the online demo green):
#   scripts/reconstruct_video.sh ../data/online/leon.webm 185 12 ../data/online/green_0305 8
#
# Needs: ffmpeg, colmap  (macOS: brew install ffmpeg colmap)
set -euo pipefail
VIDEO=$1; START=$2; DUR=$3; WORK=$4; FPS=${5:-8}

mkdir -p "$WORK/images" "$WORK/sparse" "$WORK/model_txt"
ffmpeg -v error -ss "$START" -t "$DUR" -i "$VIDEO" -vf "fps=$FPS" -q:v 2 "$WORK/images/f_%03d.jpg"
echo "frames: $(ls "$WORK/images" | wc -l)"

# Greens are smooth and evenly mowed, so few features are found with default
# settings: lower the SIFT peak threshold and allow many more features.
colmap feature_extractor --database_path "$WORK/db.db" --image_path "$WORK/images" \
  --ImageReader.single_camera 1 --ImageReader.camera_model SIMPLE_RADIAL \
  --FeatureExtraction.use_gpu 0 \
  --SiftExtraction.peak_threshold 0.0015 --SiftExtraction.max_num_features 30000
colmap sequential_matcher --database_path "$WORK/db.db" \
  --FeatureMatching.use_gpu 0 --SequentialMatching.overlap 20
colmap mapper --database_path "$WORK/db.db" --image_path "$WORK/images" --output_path "$WORK/sparse"

# keep the largest model
BEST=$(for m in "$WORK"/sparse/*/; do
  n=$(colmap model_analyzer --path "$m" 2>&1 | sed -n 's/.*Registered images: //p'); echo "$n $m"; done | sort -n | tail -1 | cut -d' ' -f2)
colmap model_converter --input_path "$BEST" --output_path "$WORK/model_txt" --output_type TXT
echo "model: $BEST -> $WORK/model_txt"
