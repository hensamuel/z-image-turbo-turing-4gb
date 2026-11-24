[Türkçe](README.tr.md) · **English** · [Deutsch](README.de.md) · [Français](README.fr.md) · [Español](README.es.md) · [Italiano](README.it.md) · [Português](README.pt.md) · [Русский](README.ru.md) · [Polski](README.pl.md) · [Nederlands](README.nl.md) · [Dansk](README.da.md) · [Norsk](README.nb.md) · [Svenska](README.sv.md) · [Suomi](README.fi.md) · [Ελληνικά](README.el.md) · [العربية](README.ar.md) · [עברית](README.he.md) · [हिन्दी](README.hi.md) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [ไทย](README.th.md) · [Tiếng Việt](README.vi.md) · [Bahasa Indonesia](README.id.md) · [Bahasa Melayu](README.ms.md) · [Tagalog](README.tl.md) · [မြန်မာ](README.my.md) · [ខ្មែរ](README.km.md) · [ລາວ](README.lo.md) · [Kiswahili](README.sw.md)

> **Turing/Linux fork (experimental):** Native CUDA builds for GTX 1650-class GPUs (SM 75) are now available as source-build scripts. See [Linux setup and validation](docs/LINUX.md). Upstream Windows/Pascal measurements below are not Turing benchmarks.


# Sınırsız Foto

**Z-Image-Turbo (Q8_0 GGUF) text-to-image at 768x1344 on a 4 GB GTX 1050 Ti (Pascal, sm_61), with stable-diffusion.cpp, on Windows.** Measured on a 16 GB RAM laptop, where the process uses about 11 GB of RAM. The same seed gives the same pixels, pixel for pixel; the measurements and the engine patches are published, the downloads are pinned with sha256, and an AI coding agent can install it step by step.

*Unofficial. Not affiliated with Tongyi-MAI (Z-Image), leejet (stable-diffusion.cpp) or NVIDIA.*

## Start here

A ready-made package exists, so try it first. If your hardware is different or a step fails, everything else is open: the patches, the build recipe and the measurements are in this repository, so you can build for your own card or adapt them.

```
1. nvidia-smi --query-gpu=name,memory.total --format=csv
      expect a line like: NVIDIA GeForce GTX 1050 Ti, 4096 MiB
      NVIDIA card with 4 GB, Windows x64 -> 2        anything else -> 5
2. python scripts/setup.py
      downloads NVIDIA cuDNN by default (NVIDIA's license applies); add --no-cudnn to skip it; both work
      expect the last line: SETUP_OK
3. python scripts/generate.py --prompt-file prompts/eiffel.txt
      expect the last line: IMAGE_OK <path>
4. Open <path>. Done. Compare your numbers: docs/MEASUREMENTS.md
5. Other hardware, or a step failed: everything is open.
      patches/README.md   docs/BUILD.md   docs/MEASUREMENTS.md   docs/TROUBLESHOOTING.md
      Build the engine for your card, or adapt the recipe. AGENTS.md has the exact steps.
```

Step 2 downloads about 12.2 GB and took 29 minutes once, on our connection; it first prints a "Preflight" block (your GPU, RAM and free disk next to what we measured; it only informs).
Only the GTX 1050 Ti 4 GB laptop card (Pascal, compute capability 6.1) was measured. Other cards were not tested.
If you use an AI coding agent (Claude Code, Codex, Cursor and similar), point it at [`AGENTS.md`](AGENTS.md).

## At a glance

Against the v0.1.0 layout: a picture takes 193–228 s instead of 261.6 s, the VAE stage takes 8.3–15.9 s instead of 29.8 to 36.3 s, the same seed gives the same pixels, and every number in this README has a command and a file behind it.

768x1344, seed 42, 8 steps, same machine. v0.1.0 numbers are from the v0.1.0 README (clean-root test and five runs); v0.2.0 numbers are from the clean-root test of this release.

| | v0.1.0 (never published; old layout) | v0.2.0 |
|---|---|---|
| Time for one picture (one `generate.py` run) | 261.6 s | 193–228 s |
| VAE decode (last stage) | 29.8 to 36.3 s | 8.3–15.9 s |
| Closeness to a reference decode (PSNR, higher is better) | 38 to 43 dB | 71 to 73 dB |
| Peak GPU memory (nvidia-smi) | 2949 to 2957 MiB | 3057–3059 MiB |
| Process memory, peak | 10.5 to 10.9 GB (as recorded then) | 10 667–10 915 MiB |
| Lowest free RAM seen | 331 to 576 MiB | 418–545 MiB |

How to read this: the reference is the same latent decoded on the CPU as one float32 piece; PSNR compares our GPU decode with it (3 pictures). It says how close the VAE stage is to that reference. It does not say how good a picture looks. The v0.2.0 pictures are not byte-identical to v0.1.0 for the same prompt and seed, because the VAE path changed on purpose. Method and the unmeasured parts: [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md).

## Examples

**AI-generated with this repo** (Z-Image-Turbo Q8_0, seed 42, 8 steps). These are not real photographs; landmarks and details
may be inaccurate, and a picture does not always follow its prompt in every detail. The exact prompts are in [`prompts/`](prompts) and [`docs/PROMPTS.md`](docs/PROMPTS.md).

| | | |
|---|---|---|
| ![Eiffel Tower at golden hour](docs/examples/eiffel.jpg) | ![Turkish tea glass](docs/examples/turkish_tea.jpg) | ![Elderly fisherman](docs/examples/fisherman.jpg) |
| `prompts/eiffel.txt`, 768x1344 | `prompts/turkish_tea.txt`, 768x1344 | `prompts/fisherman.txt`, 768x1344 |
| ![Hillside village](docs/examples/village.jpg) | | |
| `prompts/village.txt`, 768x1344 | | |

![Istanbul from the air](docs/examples/istanbul_aerial.jpg)

`prompts/istanbul_aerial.txt`, 1344x768. Not a real photo; landmarks may be inaccurate.

## Quick start

Requirements: Windows 10/11, an NVIDIA GPU with 4 GB, a driver that supports CUDA 12.8 (driver 581.29 was measured; older drivers were not tested; the CUDA runtime itself is downloaded for you), Python 3.10 or newer,
git, about 14 GB free disk (downloads are about 12.2 GB with cuDNN; the free-disk figure is an estimate), and 16 GB RAM (what was measured; less is not tested).

```powershell
git clone https://github.com/alexturkey/z-image-turbo-pascal-4gb.git
cd z-image-turbo-pascal-4gb
python scripts/setup.py
python scripts/generate.py --prompt-file prompts/eiffel.txt
```

- `setup.py` first prints a "Preflight" block (your GPU, RAM and free disk next to what we measured; it only informs and never blocks). It then downloads from the pinned addresses in [`models.lock.json`](models.lock.json) and checks every file with sha256. It prints `MODEL_OK <name>`, `ENGINE_OK`, `CUDART_OK`, then `CUDNN_OK` or `CUDNN_SKIPPED`, and finally `SETUP_OK`.
  Without `--models-dir` and `--bin-dir` it uses `models/` and `bin/` in the repo root; put the models on an SSD (only an SSD was measured).
  Stop it any time with Ctrl+C and run the same command again: downloads continue from `.part` files.
- **cuDNN is installed by default and is not part of this repository.** It is NVIDIA software under NVIDIA's own license ([license text](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/eula.html)), for systems with NVIDIA GPUs. It downloads from NVIDIA's server without payment or sign-in, and we found no clause in the license that limits commercial or personal use. `setup.py` prints the license address, downloads the file and copies only eight DLLs next to `sd-cli.exe`. NVIDIA's license says that whoever does not accept its terms must not download, install or use it; in that case run `python scripts/setup.py --no-cudnn`. Without cuDNN everything works with the slower v0.1.0 VAE path (`--vae legacy`), and `generate.py` says so.
- `generate.py` writes `outputs/<YYYYmmdd_HHMMSS>_<name>/image.png`, `run.json` (time, stages, which VAE path ran, peak GPU memory, the exact command) and `log.txt`, and prints `IMAGE_OK <path>`.

## Disk layout and removal

Everything the scripts install lives in folders you choose: the models go to `models/` (or the folder you pass with `--models-dir`), the engine and its DLLs go to `bin/` (or `--bin-dir`), and every run writes its picture and notes under `outputs/`. By default all three are inside the repository folder. The scripts use only the Python standard library: there is no pip or model cache anywhere else, and nothing is written to the system PATH, your user profile or the registry. The engine zip files sit in a temporary subfolder of the engine folder only while installing and are deleted afterwards.

Already have the model files? Pass the folder that holds them with `--models-dir`: a file with the right sha256 is kept and not downloaded again, and an interrupted download continues from its `.part` file. To see what would be downloaded and whether the disk is big enough before anything is written, run the installer with its dry-run option first (it writes nothing and opens no network connection).

**Removal:** close any running generation, then delete the folders you used (by default `models/`, `bin/` and `outputs/` in the repository folder). The repository folder itself holds only scripts and documents. That is the whole uninstall.

## Usage

```powershell
python scripts/generate.py --prompt "A lighthouse on a cliff at dawn, realistic photograph"
python scripts/generate.py --prompt-file prompts/eiffel.txt --width 1344 --height 768 --seed 7 --vae auto
```

| Option | Meaning |
|---|---|
| `--prompt "<text>"` or `--prompt-file <txt>` | the prompt (one of the two is required) |
| `--width`, `--height` | multiples of 16, 256 to 2048; default 768x1344; tested: 768x1344, 1344x768, 1024x1024 |
| `--seed` | default 42 |
| `--out`, `--name` | output folder root (default `outputs/`) and a short name for the run folder |
| `--models-dir`, `--bin-dir` | where `setup.py` put the models and the engine |
| `--vae auto` (default) | cuDNN float32; try one piece first, then two large tiles, then the small default tile |
| `--vae tiled` | cuDNN float32, always two large tiles |
| `--vae legacy` | the v0.1.0 path: no cuDNN, small tiles. Used automatically (with a warning) when the cuDNN DLLs are missing |

Steps (8), cfg (1.0), sampler and scheduler are fixed on purpose; see [What it runs](#what-it-runs).

## Check it yourself

- `generate.py` prints `PIXEL_SHA256 <hex>` as one of its last lines: a hash of the decoded pixels. Run the same command twice and compare the two pictures: `python scripts/compare.py <run A>/image.png <run B>/image.png` should print `SAME_PIXELS`.
- The `PIXEL_SHA256` of the five examples on our machine is in [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md). The file hash of a PNG can differ even when the pixels are the same, because the PNG carries the generation parameters as text; compare pixels, not files.
- Honest limit: we did not measure whether another card or driver gives the same pixels.

## Why it fits in 4 GB

- **What the model authors say.** The Z-Image-Turbo model card says the model "fits comfortably within 16G VRAM consumer devices" ([model card](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)). That is a statement about 16 GB cards. The official README also lists stable-diffusion.cpp as a third-party option and quotes it for "as little as 4GB of VRAM" ([README](https://github.com/Tongyi-MAI/Z-Image)); that is a claim of the stable-diffusion.cpp project, not a requirement of the Z-Image team.
- **What we measured.** Z-Image-Turbo Q8_0 (a 6.6 GB file) with a Qwen3-4B Q8_0 text encoder, 768x1344: the GPU peak, sampled by nvidia-smi every 2 s (a short spike can be missed), was 2949 to 2957 MiB (v0.1.0 engine) and 3057–3059 MiB (v0.2.0 engine) on a 4096 MiB card. The weights (10 509 MiB; the engine log prints it as MB) stay in system RAM; the engine copies the network to the GPU one segment (a slice of the network) at a time: 36 segments, as in the log line `z_image using 36 segments`.
- **What it costs.** Time and system memory: 193–228 s per picture, and the engine process holds about 10 667–10 915 MiB of RAM (memory-mapped model pages included) on a 16 GB machine, so free RAM drops to a few hundred MiB while it runs.
- **Other people's setups.** Others report Z-Image on 4 GB cards with lower quantization or smaller sizes (for example the stable-diffusion.cpp wiki page for 4 GB cards recommends Q3_K or Q4_0 at 1024x512). Where we looked (list and date in [`docs/RELATED.md`](docs/RELATED.md)) we did not find a published setup that combines all four: a 4 GB card, Q8_0, 768x1344 or larger, and measured time and GPU memory. That is a statement about where we looked, not about everywhere.
- **Who does what.** Fitting into 4 GB comes from stable-diffusion.cpp itself: `--offload-to-cpu`, `--mmap`, working in slices, and flash attention (with it off, a run needed 4205 MB and did not fit). Our patches are for speed and for a better VAE stage, not for fitting. We did not run the unpatched upstream engine on this card, so we cannot say whether it fits.

## How it works

Three changes on top of stable-diffusion.cpp `master-1088-32d516c` (all are switches; the table in [`patches/README.md`](patches/README.md) lists each one with its environment variable):

1. **The refiner runs once per step.** A group name was used twice, so four refiner blocks were computed a second time. Fixing it makes steps 2 to 8 about 1.3 s faster each (22.0 to 20.7 s) with a pixel-identical picture (3 pictures checked).
2. **VAE through cuDNN, in float32.** The last stage (turning the latent into pixels) now uses NVIDIA's cuDNN float32 convolution. On our card it took the VAE from 23 to 27 s to 10 to 15 s and moved the PSNR against the reference from 38 to 43 dB to 45 to 49 dB (large tiles).
3. **One piece first.** The engine now tries to decode the whole image in one piece when the memory check says it fits (margin 256 MiB), falls back to two large tiles, and then to small tiles. In one piece the VAE took about 8–16 s and the PSNR against the reference was 71 to 73 dB. If a forced fallback happens, the picture has the same pixels as the tiled one (checked with `PIXEL_SHA256`). What happened is written in `run.json` (`stages.vae_path`: `full`, `tile`, `floor` or `retry`).

Also: `--eager-load` (reads the model pages up front; 241.2 s to 220.3 s on the same picture, development build, one run each) is part of the fixed command.

<a id="what-it-runs"></a>
## What it runs

| Part | File | Source |
|---|---|---|
| Diffusion model | `z_image_turbo-Q8_0.gguf` (6,577,440,704 B) | [leejet/Z-Image-Turbo-GGUF](https://huggingface.co/leejet/Z-Image-Turbo-GGUF), base [Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) |
| Text encoder | `Qwen3-4B-Instruct-2507-Q8_0.gguf` (4,280,405,600 B) | [unsloth/Qwen3-4B-Instruct-2507-GGUF](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) |
| VAE | `ae.safetensors` (335,304,388 B) | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo), FLUX.1-type autoencoder |
| Engine | `sd-cli.exe`, stable-diffusion.cpp `32d516c` with the patches in [`patches/`](patches) | the v0.2.0 release of this repository (`sinirsiz-foto-engine-v0.2.0-win-x64-cuda12.8-sm61.zip`) |
| CUDA runtime | `cudart`, `cublas`, `cublasLt` (12.8), unmodified | zip from the wan22-pascal-4gb v0.1.0 release |
| cuDNN (installed by default; `--no-cudnn` skips it) | 8 DLLs, version 9.10.2.21 (CUDA 11 build) | NVIDIA's own server, under NVIDIA's license; not stored here |

Fixed settings: `--cfg-scale 1.0 --steps 8 --sampling-method euler --scheduler simple --offload-to-cpu --mmap --eager-load --flash-attn on`.
We do not lower the steps, add a negative prompt or enable caching: the model is distilled for 8 steps and does not use negative prompts (see [prompts](docs/PROMPTS.md)).

## Limits (read before you rely on it)

- **Windows only.** The prebuilt engine and these scripts are Windows only.
- **One card, one machine.** Measured only on a GTX 1050 Ti 4 GB laptop (i7-7700HQ, 16 GB RAM, Windows 10, driver 581.29, models on an SSD). Other GPUs and drivers, machines with less than 16 GB RAM, Linux and macOS: **not tested by us**.
- Other cards and systems (which path exists, and a community test on an AMD card under Linux that we did not run ourselves): [docs/OTHER_GPUS.md](docs/OTHER_GPUS.md).
- **The engine is built for Pascal (sm_61) only.** Other architectures need a build of your own ([`docs/BUILD.md`](docs/BUILD.md)); we did not test one.
- **cuDNN:** we measured with the CUDA 11 build of cuDNN 9.10.2.21. The CUDA 12 build has different files and was not measured.
- **Memory is tight.** Free RAM falls to a few hundred MiB; close other programs, run one picture at a time. We have not seen GPU memory run out after the engine's memory check passed, and we did not test what happens then.
- **Sizes:** only 768x1344, 1344x768 and 1024x1024 were tested. Bigger sizes print a warning and may run out of memory.
- Prompt fidelity is partial: a picture does not always follow its prompt in every detail. Text inside pictures and real-world landmarks were not evaluated.
- The PSNR reference is our own engine's CPU decode, not an independent implementation.
- Numbers in [`docs/MEASUREMENTS.md`](docs/MEASUREMENTS.md) come from one run each unless it says otherwise.

## License and credit

- This repository's scripts and documents: [Apache-2.0](LICENSE) with a [`NOTICE`](NOTICE) file. The engine patches in [`patches/`](patches) are MIT, like the code they modify.
- stable-diffusion.cpp and ggml are MIT. Notices for the third-party code compiled into the engine are in [`licenses/`](licenses) and [`THIRD_PARTY.md`](THIRD_PARTY.md).
- Model files are not stored here; they are downloaded from the sources above under their own licenses (Hugging Face lists Apache-2.0 for all of them, read on 2026-11-13). The model card says nothing about who owns generated pictures, and we make no claim about it.
- **cuDNN and the CUDA runtime are NVIDIA's property** and are not under this repository's license. cuDNN is downloaded from NVIDIA's server under NVIDIA's license (`--no-cudnn` skips it); the CUDA runtime DLLs are in a separate unmodified zip (CUDA Toolkit EULA, Attachment A). Details and what we could not verify: [`THIRD_PARTY.md`](THIRD_PARTY.md).
- **Credit.** Keeping the `NOTICE` file with copies and derived works is the condition (Apache-2.0, section 4). Beyond that, a line such as "Based on Sınırsız Foto by Ali Haydar Öztürk (Ozturk), https://github.com/alexturkey" is appreciated, not required.
- Please read [`ETHICS.md`](ETHICS.md): every picture is synthetic, and you are responsible for what you publish.

## Contributing

The most useful thing you can do is **test your card** and tell us what happened: GPU name, driver, RAM, the `run.json` and the last lines of the log (the "Hardware test report" issue form). Fixes to the documents and to the scripts are welcome too; see [`CONTRIBUTING.md`](CONTRIBUTING.md). Security reports go through the private route in [`SECURITY.md`](SECURITY.md).

[Install guide for AI agents](AGENTS.md) · [Measurements](docs/MEASUREMENTS.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Building the engine](docs/BUILD.md) · [Patches](patches/README.md) · [Prompts](docs/PROMPTS.md) · [Third-party](THIRD_PARTY.md) · [Changelog](CHANGELOG.md)
