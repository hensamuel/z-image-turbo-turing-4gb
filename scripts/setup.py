#!/usr/bin/env python3
"""Download and verify everything needed to run sinirsiz-foto (Windows, Python 3.10+, standard library only).

What it does (reads models.lock.json in the repo root):
  * downloads the three model files from pinned Hugging Face commits  -> <models-dir>
  * downloads the engine zip and the CUDA runtime zip from our release -> <bin-dir>
  * downloads NVIDIA's official cuDNN archive from NVIDIA's server and copies only the runtime DLLs next to
    sd-cli.exe. This repository does not contain or redistribute cuDNN. It is proprietary NVIDIA software under
    NVIDIA's own license: installing it means accepting that license. Setup prints the license address before the
    download and keeps a local record. Pass --no-cudnn to skip it; everything still works, and generate.py then
    uses the slower v0.1.0 VAE path (--vae legacy).
  * resumes interrupted downloads (<name>.part), checks size and sha256 of every file
  * never uses "main" / "latest": the lock file pins commits, release tags and one versioned NVIDIA archive

Usage:
  python scripts/setup.py [--models-dir DIR] [--bin-dir DIR] [--lock FILE] [--only models|engine|cudnn] [--check]
                          [--no-cudnn]

Defaults: models/ and bin/ in the repo root. The models are about 11 GB: put --models-dir on an SSD.
First it prints a preflight block (GPU, driver, RAM, free disk) before any download; it informs, it does not block.
Success lines: MODEL_OK <name>, ENGINE_OK, CUDART_OK, CUDNN_OK (or CUDNN_SKIPPED), final line SETUP_OK.
With --only the final line is SETUP_PART_OK <part> instead: one part is not the whole setup.
--accept-cudnn-license is still accepted and does nothing (cuDNN is installed by default since v0.2.0).
Exit code 0 on success.
--dry-run prints the plan (what would be fetched, free disk) and writes nothing; it ends with DRYRUN_OK (exit 0) or an ERROR line (exit 3).
Stop with Ctrl+C; run the same command again to continue where it stopped.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHUNK = 1024 * 1024
RETRIES = 6
USER_AGENT = "sinirsiz-foto-setup/2"
CUDNN_RECORD = "cudnn_license_record.json"
CUDNN_MODE = "default_download_disclosed"


def load_lock(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("models", "engine"):
        if not isinstance(data.get(key), list) or not data[key]:
            raise ValueError("lock file has no '%s' list" % key)
    return data


def sha256_file(path, label=None, quiet=False):
    h = hashlib.sha256()
    total = Path(path).stat().st_size
    done = 0
    next_mark = 10
    with open(path, "rb") as f:
        while True:
            b = f.read(8 * CHUNK)
            if not b:
                break
            h.update(b)
            done += len(b)
            if not quiet and total > 200 * CHUNK and done * 100 // total >= next_mark:
                print("  hashing %s ... %d%%" % (label or Path(path).name, done * 100 // total), flush=True)
                next_mark += 10
    return h.hexdigest()


def is_verified(path, entry):
    p = Path(path)
    if not p.is_file() or p.stat().st_size != entry["bytes"]:
        return False
    return sha256_file(p, entry["name"]) == entry["sha256"]


def _open(url, start):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    if start > 0:
        req.add_header("Range", "bytes=%d-" % start)
    return urllib.request.urlopen(req, timeout=60)


def download(url, dest, size, sha256, label=None):
    """Download url to dest through dest+'.part' (resumable). Returns True when verified.

    Raises RuntimeError on a hash mismatch (the bad file is removed) or when retries run out.
    """
    dest = Path(dest)
    label = label or dest.name
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, RETRIES + 1):
        have = part.stat().st_size if part.exists() else 0
        if have > size:
            part.unlink()
            have = 0
        try:
            if have < size:
                with _open(url, have) as r:
                    status = getattr(r, "status", 200)
                    if have and status != 206:
                        have = 0                      # server ignored Range: start over
                    mode = "ab" if have else "wb"
                    got = have
                    next_mark = (got * 100 // size // 10 + 1) * 10 if size else 100
                    t0 = time.time()
                    with open(part, mode) as out:
                        while True:
                            b = r.read(CHUNK)
                            if not b:
                                break
                            out.write(b)
                            got += len(b)
                            if size and got * 100 // size >= next_mark:
                                rate = (got - have) / max(time.time() - t0, 1e-6) / CHUNK
                                print("  %s %d%% (%.1f MiB/s)" % (label, got * 100 // size, rate), flush=True)
                                next_mark += 10
            if part.stat().st_size != size:
                raise OSError("incomplete: %d of %d bytes" % (part.stat().st_size, size))
            break
        except urllib.error.HTTPError as e:
            if e.code == 416 and part.exists() and part.stat().st_size == size:
                break                                 # already complete
            if e.code in (401, 403, 404):
                raise RuntimeError("%s: HTTP %d for %s" % (label, e.code, url))
            last_err = e
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            last_err = e
        if attempt == RETRIES:
            raise RuntimeError("%s: download failed after %d tries (%s). Run setup again to resume." % (label, RETRIES, last_err))
        wait = min(60, 3 * attempt * attempt)
        print("  %s: %s; retry %d/%d in %d s" % (label, last_err.__class__.__name__, attempt, RETRIES - 1, wait), flush=True)
        time.sleep(wait)

    got_hash = sha256_file(part, label)
    if got_hash != sha256:
        part.unlink()
        raise RuntimeError("%s: sha256 mismatch (expected %s, got %s). The partial file was removed; run again." % (label, sha256, got_hash))
    part.replace(dest)
    return True


def safe_extract(zip_path, target):
    """Extract a zip refusing paths that escape the target folder. Returns the list of extracted files."""
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            dest = (target / info.filename).resolve()
            if target != dest and target not in dest.parents:
                raise RuntimeError("unsafe path in zip: %s" % info.filename)
            z.extract(info, target)
            if not info.is_dir():
                out.append(dest)
    return out


def find_sd_cli(bin_dir):
    bin_dir = Path(bin_dir)
    direct = bin_dir / "sd-cli.exe"
    if direct.is_file():
        return direct
    for p in sorted(bin_dir.rglob("sd-cli.exe")):
        return p
    return None


def has_cudart(bin_dir):
    bin_dir = Path(bin_dir)
    return any(bin_dir.rglob("cudart64_*.dll"))


def cudnn_dir(bin_dir):
    """cuDNN DLLs go next to sd-cli.exe (the engine loads them from its own folder)."""
    sd = find_sd_cli(bin_dir)
    return sd.parent if sd else Path(bin_dir)


def cudnn_installed(bin_dir, entry):
    """True when every DLL named in the lock entry is present with the right size."""
    d = cudnn_dir(bin_dir)
    for m in entry["members"]:
        p = d / Path(m["path"]).name
        if not p.is_file() or p.stat().st_size != m["bytes"]:
            return False
    return True


def extract_members(zip_path, entry, target):
    """Copy only the listed members (flat, by file name) out of the archive; size and CRC32 are checked.

    Returns the list of written files. Nothing else in the archive is extracted.
    """
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    wanted = list(entry["members"])
    if entry.get("license_member"):
        wanted.append({"path": entry["license_member"], "save_as": entry.get("license_save_as", "LICENSE.txt")})
    out = []
    with zipfile.ZipFile(zip_path) as z:
        for m in wanted:
            try:
                info = z.getinfo(m["path"])
            except KeyError:
                raise RuntimeError("%s: %s is not in the archive" % (entry["name"], m["path"]))
            if "bytes" in m and info.file_size != m["bytes"]:
                raise RuntimeError("%s: %s has %d bytes, the lock says %d" % (entry["name"], m["path"], info.file_size, m["bytes"]))
            if "crc32" in m and "%08x" % info.CRC != m["crc32"].lower():
                raise RuntimeError("%s: %s CRC32 does not match the lock" % (entry["name"], m["path"]))
            name = m.get("save_as") or Path(m["path"]).name
            if Path(name).name != name:
                raise RuntimeError("unsafe file name in lock: %s" % name)
            dest = target / name
            tmp = dest.with_name(dest.name + ".part")
            with z.open(info) as src, open(tmp, "wb") as dst:      # zipfile verifies the CRC while reading
                shutil.copyfileobj(src, dst, 8 * CHUNK)
            tmp.replace(dest)
            out.append(dest)
    return out


def write_cudnn_record(target, entry, how):
    """Keep a local record of the install: which license text (sha256), which archive, when, and that it was the
    disclosed default (nobody was asked; the license address was printed before the download)."""
    target = Path(target)
    lic = target / entry.get("license_save_as", "LICENSE.txt")
    record = {
        "archive": entry["name"],
        "archive_sha256": entry["sha256"],
        "version": entry.get("version", ""),
        "license_url": entry.get("license_url", ""),
        "license_file": lic.name,
        "license_sha256": sha256_file(lic, quiet=True) if lic.is_file() else None,
        "installed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": how,
    }
    dest = target / CUDNN_RECORD
    dest.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return dest


def check_disk(path, need_bytes):
    Path(path).mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    if free < need_bytes:
        print("ERROR: %s has %.1f GiB free, about %.1f GiB is needed. Fix: free disk space, or choose another drive "
              "with --models-dir / --bin-dir, then run the same command again." % (path, free / 2**30, need_bytes / 2**30))
        return False
    return True


def machine_report():
    """What this machine has, read before anything is downloaded. Missing tools give None, never an error."""
    info = {"gpu": None, "ram_total_mib": None}
    exe = shutil.which("nvidia-smi")
    if exe:
        try:
            r = subprocess.run([exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=15,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and r.stdout.strip():
                name, mem, driver = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")[:3]]
                info["gpu"] = {"name": name, "memory_total_mib": int(mem), "driver": driver}
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
            ms = MS()
            ms.l = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                info["ram_total_mib"] = int(ms.total // (1024 * 1024))
        except (OSError, AttributeError):
            pass
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    info["ram_total_mib"] = int(line.split()[1]) // 1024
                    break
        except (OSError, ValueError, IndexError):
            pass
    return info


def preflight(models_dir, bin_dir, out=print, create=True):
    """Print the machine facts next to what was measured. Only information: nothing here stops the setup."""
    info = machine_report()
    out("Preflight (measured on: GTX 1050 Ti 4 GB laptop, sm_61 / Pascal, 16 GB RAM, Windows 10; see docs/MEASUREMENTS.md)")
    g = info["gpu"]
    if g is None:
        out("  GPU      : nvidia-smi not found or no NVIDIA GPU. WARNING: the engine needs an NVIDIA GPU with CUDA; "
            "see docs/TROUBLESHOOTING.md")
    else:
        out("  GPU      : %s, %d MiB, driver %s" % (g["name"], g["memory_total_mib"], g["driver"]))
        if g["memory_total_mib"] < 4000:
            out("  WARNING  : less than 4 GB of GPU memory was never tested")
    r = info["ram_total_mib"]
    if r is None:
        out("  RAM      : unknown")
    else:
        out("  RAM      : %d MiB total" % r)
        if r < 15000:
            out("  WARNING  : the process uses about 11 GB (measured); less than 16 GB of RAM was never tested")
    for label, path in (("models", models_dir), ("engine", bin_dir)):
        try:
            if create:
                Path(path).mkdir(parents=True, exist_ok=True)
            out("  Disk     : %.1f GiB free for %s in %s" % (shutil.disk_usage(existing_parent(path)).free / 2**30, label, path))
        except OSError:
            out("  Disk     : cannot read free space for %s" % path)
    return info


def existing_parent(path):
    """The folder itself, or its nearest existing parent (so free space can be read without creating anything)."""
    p = Path(path).absolute()
    while not p.exists() and p.parent != p:
        p = p.parent
    return p


def dry_run(lock, models_dir, bin_dir, no_cudnn, out=print):
    """Everything setup would do, printed; writes nothing, creates no folder, opens no network connection.

    Exit code 0 and the last line DRYRUN_OK when the free disk space is enough, 3 and an ERROR line when it is not.
    """
    preflight(models_dir, bin_dir, out, create=False)
    need_models = need_bin = 0
    for m in lock["models"]:
        dest = Path(models_dir) / m["name"]
        if dest.is_file() and dest.stat().st_size == m["bytes"]:
            out("  would keep   %s (present, size matches; sha256 is read by a real run or --check)" % m["name"])
            continue
        part = Path(models_dir) / (m["name"] + ".part")
        have = part.stat().st_size if part.is_file() else 0
        need_models += max(m["bytes"] - have, 0)
        out("  would fetch  %s (%.2f GiB%s)" % (m["name"], m["bytes"] / 2**30, ", resumes a .part file" if have else ""))
    if not sys.platform.startswith("linux") and not (find_sd_cli(bin_dir) and has_cudart(bin_dir)):
        for e in lock["engine"]:
            need_bin += e["bytes"] * 2
            out("  would fetch  %s (%.1f MiB)" % (e["name"], e["bytes"] / 2**20))
    c = lock.get("cudnn")
    if isinstance(c, dict) and not no_cudnn and not cudnn_installed(bin_dir, c):
        need_bin += c["bytes"] + sum(x["bytes"] for x in c["members"])
        out("  would fetch  %s from NVIDIA (%.1f MiB), under NVIDIA's license: %s. --no-cudnn skips it."
            % (c["name"], c["bytes"] / 2**20, c["license_url"]))
    ok = True
    for label, path, need in (("models", models_dir, need_models), ("engine", bin_dir, need_bin)):
        if not need:
            continue
        free = shutil.disk_usage(existing_parent(path)).free
        out("  Need     : about %.1f GiB for %s, %.1f GiB free" % (need / 2**30, label, free / 2**30))
        if free < need + 512 * CHUNK:
            ok = False
            out("ERROR: %s has %.1f GiB free, about %.1f GiB is needed. Fix: free disk space, or choose another drive "
                "with --models-dir / --bin-dir, then run the same command again." % (path, free / 2**30, need / 2**30))
    if ok:
        out("DRYRUN_OK (nothing was downloaded or written)")
        return 0
    return 3


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models-dir", default=str(ROOT / "models"), help="where the model files go (default: ./models; an SSD is recommended)")
    ap.add_argument("--bin-dir", default=str(ROOT / "bin"), help="where sd-cli.exe and the CUDA DLLs go (default: ./bin)")
    ap.add_argument("--lock", default=str(ROOT / "models.lock.json"), help="lock file (default: models.lock.json)")
    ap.add_argument("--only", choices=("models", "engine", "cudnn"), help="do only one part")
    ap.add_argument("--check", action="store_true", help="verify files that are already there; download nothing")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would be downloaded and whether the disk is enough; writes nothing, no network")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--accept-cudnn-license", action="store_true",
                   help="kept for old command lines; does nothing (cuDNN is installed by default)")
    g.add_argument("--no-cudnn", action="store_true",
                   help="do not download NVIDIA cuDNN (generate.py then uses --vae legacy)")
    a = ap.parse_args(argv)

    try:
        lock = load_lock(a.lock)
    except (OSError, ValueError) as e:
        print("ERROR: cannot read lock file: %s. Fix: run from a complete copy of the repository, or pass --lock FILE." % e)
        return 2
    models_dir, bin_dir = Path(a.models_dir), Path(a.bin_dir)
    if sys.platform.startswith("linux"):
        if a.only in ("engine", "cudnn"):
            print("ERROR: Windows binary archives are not supported on Linux. See docs/LINUX.md.")
            return 2
        a.only = "models"
        a.no_cudnn = True
        print("Linux: model setup only; build the native engine with bash scripts/build-linux.sh.")
    if a.dry_run:
        return dry_run(lock, models_dir, bin_dir, a.no_cudnn)
    do_models = a.only in (None, "models")
    do_engine = a.only in (None, "engine")
    do_cudnn = a.only in (None, "cudnn") and isinstance(lock.get("cudnn"), dict)
    if not a.check:
        preflight(models_dir, bin_dir)

    try:
        if do_models:
            need = 0
            for m in lock["models"]:
                if not (models_dir / m["name"]).is_file():
                    part = models_dir / (m["name"] + ".part")
                    need += m["bytes"] - (part.stat().st_size if part.exists() else 0)
            if need and not a.check and not check_disk(models_dir, need + 512 * CHUNK):
                return 2
            for m in lock["models"]:
                dest = models_dir / m["name"]
                if is_verified(dest, m):
                    print("MODEL_OK %s" % m["name"])
                    continue
                if a.check:
                    print("MODEL_MISSING_OR_BAD %s" % m["name"])
                    return 1
                if dest.exists():
                    print("  %s is present but does not match the lock; downloading again" % m["name"])
                    dest.unlink()
                print("Downloading %s (%.2f GiB)" % (m["name"], m["bytes"] / 2**30), flush=True)
                download(m["url"], dest, m["bytes"], m["sha256"], m["name"])
                print("MODEL_OK %s" % m["name"])

        if do_engine:
            marker = bin_dir / ".engine_installed.json"
            wanted = {e["name"]: e["sha256"] for e in lock["engine"]}
            try:
                installed = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                installed = None
            if installed != wanted or not find_sd_cli(bin_dir) or not has_cudart(bin_dir):
                if a.check:
                    print("ENGINE_MISSING_OR_OLD")
                    return 1
                zips = []
                for e in lock["engine"]:
                    zp = bin_dir / "_downloads" / e["name"]
                    if not is_verified(zp, e):
                        if zp.exists():
                            zp.unlink()
                        if not check_disk(bin_dir, e["bytes"] * 2 + 256 * CHUNK):
                            return 2
                        print("Downloading %s (%.1f MiB)" % (e["name"], e["bytes"] / 2**20), flush=True)
                        download(e["url"], zp, e["bytes"], e["sha256"], e["name"])
                    zips.append(zp)
                for zp in zips:
                    safe_extract(zp, bin_dir)
                shutil.rmtree(bin_dir / "_downloads", ignore_errors=True)   # install source only
                marker.write_text(json.dumps(wanted, indent=1), encoding="utf-8")
            if not find_sd_cli(bin_dir):
                print("ERROR: sd-cli.exe not found in %s after unpacking. Fix: delete that folder and run "
                      "python scripts/setup.py --only engine again." % bin_dir)
                return 1
            print("ENGINE_OK")
            if not has_cudart(bin_dir):
                print("ERROR: cudart64_*.dll not found in %s after unpacking. Fix: delete that folder and run "
                      "python scripts/setup.py --only engine again." % bin_dir)
                return 1
            print("CUDART_OK")

        if do_cudnn:
            c = lock["cudnn"]
            if cudnn_installed(bin_dir, c):
                print("CUDNN_OK")
            elif a.check or a.no_cudnn:
                print("CUDNN_SKIPPED (not installed; generate.py will use --vae legacy)")
            elif not find_sd_cli(bin_dir):
                print("ERROR: sd-cli.exe not found in %s. Fix: install the engine first with "
                      "python scripts/setup.py --only engine" % bin_dir)
                return 1
            else:
                zp = bin_dir / "_downloads" / c["name"]
                if not is_verified(zp, c):
                    if zp.exists():
                        zp.unlink()
                    unpacked = sum(m["bytes"] for m in c["members"])
                    if not check_disk(bin_dir, c["bytes"] + unpacked + 256 * CHUNK):
                        return 2
                    print("Downloading NVIDIA cuDNN under NVIDIA's license: %s. Use --no-cudnn to skip."
                          % c["license_url"], flush=True)
                    print("Downloading %s from NVIDIA (%.1f MiB)" % (c["name"], c["bytes"] / 2**20), flush=True)
                    download(c["url"], zp, c["bytes"], c["sha256"], c["name"])
                extract_members(zp, c, cudnn_dir(bin_dir))
                write_cudnn_record(cudnn_dir(bin_dir), c, CUDNN_MODE)
                shutil.rmtree(bin_dir / "_downloads", ignore_errors=True)   # install source only
                if not cudnn_installed(bin_dir, c):
                    print("ERROR: cuDNN DLLs are incomplete in %s. Fix: run python scripts/setup.py --only cudnn again; "
                          "see docs/TROUBLESHOOTING.md." % cudnn_dir(bin_dir))
                    return 1
                print("CUDNN_OK")
    except RuntimeError as e:
        print("ERROR: %s. Fix: run the same command again (downloads resume); if it repeats, see "
              "docs/TROUBLESHOOTING.md." % str(e).rstrip("."))
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Run the same command again to continue.")
        return 130

    if a.only:
        print("SETUP_PART_OK %s" % a.only)     # one part only: not the whole setup
    else:
        print("SETUP_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
