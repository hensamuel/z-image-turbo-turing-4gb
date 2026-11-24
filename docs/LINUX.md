# Linux / NVIDIA Turing (experimental)

This fork targets 4 GiB Turing cards such as GTX 1650 (SM 75). The original Windows/Pascal release and its measurements remain upstream evidence, not Linux benchmarks. Native Linux compilation and GPU inference are not yet validated. No Wine, Wayland or X11-specific dependencies are needed by the CLI.

## Dependencies

Python 3.10+, git, CMake, Ninja, C/C++ compiler compatible with the installed CUDA toolkit, NVIDIA driver and CUDA development toolkit. CUDA 12.8 is the upstream reference; CUDA 13 is experimental for this source revision. Check:

```sh
nvidia-smi
nvcc --version
gcc --version
free -h
```

On Arch/CachyOS: `sudo pacman -S --needed base-devel git cmake ninja python cuda`. If the toolkit does not accept the system GCC version, use a toolkit-supported compiler (do not bypass the compiler version check). If nvcc is outside PATH, set CUDACXX to its absolute path. Ensure sufficient SSD space for the build and approximately 12 GB of model downloads, and close memory-heavy applications.

## Build and run

From the repository root:

```sh
bash scripts/build-linux.sh
python scripts/setup.py --only models --no-cudnn
python scripts/generate.py --bin-dir .build-linux/turing-sm75/sdcpp/build/bin --vae legacy --prompt-file prompts/eiffel.txt --width 512 --height 512
```

The setup script verifies downloaded models against the existing lock file; it never installs Windows engine archives on Linux. The native build currently disables cuDNN; legacy VAE is required. The build script manages a disposable source checkout under .build-linux and resets its tracked files each run. Do not edit that checkout to store personal changes.

Default profile keeps generic memory and Z-Image patches but omits the three Pascal-tuned ggml kernels. To compare with the full upstream patch set, run `env PATCH_PROFILE=original bash scripts/build-linux.sh` and use `.build-linux/original-sm75/sdcpp/build/bin` for generation. Set JOBS to adjust parallel compilation. CUDA_ARCH defaults to 75. These profiles are experimental; no performance advantage is claimed.

## Validation

Check that sd-cli --help works, then look for IMAGE_OK and inspect outputs/*/run.json and log.txt. Verify the CUDA backend actually loads, inspect GPU memory with nvidia-smi, and compare peak RAM/VRAM and generation time using identical seed, prompt and dimensions. Only after 512x512 succeeds try 768x1344. Keep original Pascal measurements separate. Report compiler errors verbatim; do not change source revisions to fix them without checking patch compatibility.

Next work: native cuDNN detection and build support, CUDA 13 compatibility verification, hardware benchmarks and Windows regression tests.
