#!/usr/bin/env bash
# Native CUDA build; run with bash scripts/build-linux.sh.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
arch="${CUDA_ARCH:-75}"
profile="${PATCH_PROFILE:-turing}"
jobs="${JOBS:-4}"
src="$root/.build-linux/$profile-sm$arch/sdcpp"
case "$profile" in turing|original) ;; *) echo "Invalid PATCH_PROFILE" >&2; exit 2;; esac
[[ "$arch" =~ ^[0-9]+$ && "$jobs" =~ ^[1-9][0-9]*$ ]] || exit 2
for cmd in git cmake ninja; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 2; }; done
nvcc="${CUDACXX:-$(command -v nvcc || true)}"
if [[ -z "$nvcc" && -x /opt/cuda/bin/nvcc ]]; then nvcc=/opt/cuda/bin/nvcc; fi
[[ -n "$nvcc" ]] || { echo "Install CUDA Toolkit or set CUDACXX" >&2; exit 2; }
"$nvcc" --version
mkdir -p "$(dirname "$src")"
if [[ ! -d "$src/.git" ]]; then
  git -c core.autocrlf=false clone https://github.com/leejet/stable-diffusion.cpp.git "$src"
fi
# Only reset files in our dedicated disposable build checkout.
git -C "$src" reset --hard
git -C "$src" checkout --detach 32d516c
git -C "$src" submodule update --init --recursive
git -C "$src/ggml" reset --hard
git -C "$src/ggml" checkout --detach d803c23
if [[ "$profile" == original ]]; then
  git -C "$src/ggml" apply "$root"/patches/ggml/0001-*.patch "$root"/patches/ggml/0002-*.patch "$root"/patches/ggml/0003-*.patch
fi
git -C "$src/ggml" apply "$root"/patches/ggml/0006-*.patch "$root"/patches/ggml/0009-*.patch
git -C "$src" apply "$root"/patches/sdcpp/0004-*.patch "$root"/patches/sdcpp/0012-*.patch "$root"/patches/sdcpp/0022b-*.patch "$root"/patches/sdcpp/0025-*.patch "$root"/patches/sdcpp/0027-*.patch "$root"/patches/sdcpp/0028b-*.patch "$root"/patches/sdcpp/0029-*.patch
cmake -S "$src" -B "$src/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_COMPILER="$nvcc" \
  -DCMAKE_CUDA_ARCHITECTURES="$arch" \
  -DSD_CUDA=ON -DGGML_NATIVE=OFF \
  -DGGML_BACKEND_DL=ON -DSD_BUILD_SHARED_LIBS=ON \
  -DSD_BUILD_SHARED_GGML_LIB=ON -DGGML_CUDA_CUDNN_CONV2D_F32=OFF
cmake --build "$src/build" --parallel "$jobs"
bin="$src/build/bin"
test -x "$bin/sd-cli"
LD_LIBRARY_PATH="$bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$bin/sd-cli" --help
echo "Engine directory: $bin"
echo "Use: python scripts/generate.py --bin-dir '$bin' --vae legacy --prompt-file prompts/eiffel.txt --width 512 --height 512"
