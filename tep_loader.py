"""Download and load the Tennessee Eastman Process (TEP) simulation data from Rieth et al. (2017).

Source: https://doi.org/10.7910/DVN/6C3JR1 (Harvard Dataverse). Four R data files:
fault-free and faulty, each as a training set (500 readings per run) and a testing set (960 readings).
Readings are 3 minutes apart. Every set has 500 runs per fault, and fault 0 means no fault.

Needs: pandas and pyreadr (pip install pandas pyreadr). The faulty training file has 20 faults x 500 runs x
500 readings = 5 million rows, so loading all of it takes time and several GB of memory. Ask for fewer faults
or runs when you can.

Example:
    from tep_loader import load_tep
    df, checks = load_tep(kind="both", faults=[0, 2], runs=range(1, 11))
    print(checks)

STATUS: the download step (list_files / download) has not been run against the real Dataverse server.
If it fails, download the .RData files in a browser from the page above, put them in the data folder,
and run again; the loader uses files it finds there.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

SERVER = "https://dataverse.harvard.edu"
DATASET = "doi:10.7910/DVN/6C3JR1"
PAGE = f"{SERVER}/dataset.xhtml?persistentId={DATASET}"

FILES = {
    ("fault_free", "training"): "TEP_FaultFree_Training.RData",
    ("fault_free", "testing"): "TEP_FaultFree_Testing.RData",
    ("faulty", "training"): "TEP_Faulty_Training.RData",
    ("faulty", "testing"): "TEP_Faulty_Testing.RData",
}
READINGS_PER_RUN = {"training": 500, "testing": 960}
MINUTES_PER_READING = 3.0
SHUTDOWN_KPA = 3000.0


# ---------------------------------------------------------------- download

def _get(url, server):
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{server} answered {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach {server}: {e.reason}") from e


def list_files(server=SERVER):
    """Return {file name: file id} for the latest published version of the dataset."""
    query = urllib.parse.urlencode({"persistentId": DATASET})
    url = f"{server}/api/datasets/:persistentId/versions/:latest-published/files?{query}"
    listing = json.loads(_get(url, server))
    files = {}
    for entry in listing["data"]:
        info = entry["dataFile"]
        # Dataverse may convert a file it recognizes as a table; the original name is kept separately.
        files[info.get("originalFileName") or info["filename"]] = info["id"]
    return files


def download(filename, data_dir, server=SERVER):
    """Download one dataset file into data_dir (original format) and return its path."""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    available = list_files(server)
    if filename not in available:
        raise RuntimeError(f"{filename} is not in the dataset listing. Files found: {sorted(available)}")
    url = f"{server}/api/access/datafile/{available[filename]}?format=original"
    content = _get(url, server)
    if content[:1] == b"<" or len(content) < 1_000_000:
        raise RuntimeError(f"Downloaded {len(content):,} bytes that do not look like the data file "
                           f"(starts with {content[:40]!r}). Download it by hand from {PAGE}")
    path = data_dir / filename
    path.write_bytes(content)
    return path


def ensure_file(kind, split, data_dir, server=SERVER):
    """Return the local path of one data file, downloading it first if it is not in data_dir."""
    filename = FILES[(kind, split)]
    path = Path(data_dir) / filename
    if path.exists():
        return path
    try:
        return download(filename, data_dir, server)
    except RuntimeError as e:
        raise RuntimeError(f"{e}\nTo continue by hand: download {filename} from {PAGE} and put it in "
                           f"'{data_dir}'.") from e


# ---------------------------------------------------------------- reading

def _read_rdata(path):
    """Read an R data file holding one data frame and return it as a pandas table."""
    import pyreadr
    return next(iter(pyreadr.read_r(str(path)).values()))


def _load_one(kind, split, data_dir, server):
    return _read_rdata(ensure_file(kind, split, data_dir, server))


def load_tep(kind="both", split="training", faults=None, runs=None, data_dir="tep_data",
             dictionary="tep_data_dictionary.csv", server=SERVER):
    """Return (table, checks).

    kind:   "fault_free", "faulty" or "both"
    split:  "training" or "testing"
    faults: fault numbers to keep (0 = no fault, 1-20 = faults), or None for all
    runs:   run numbers to keep (1-500), or None for all
    The dictionary file renames the columns and says what each one is.
    """
    if kind not in ("fault_free", "faulty", "both"):
        raise ValueError("kind must be 'fault_free', 'faulty' or 'both'")
    if split not in READINGS_PER_RUN:
        raise ValueError("split must be 'training' or 'testing'")

    d = pd.read_csv(dictionary, keep_default_na=False)
    kinds = ["fault_free", "faulty"] if kind == "both" else [kind]
    parts = []
    for k in kinds:
        df = _load_one(k, split, data_dir, server)
        missing = sorted(set(d.raw_name) - set(df.columns))
        extra = sorted(set(df.columns) - set(d.raw_name))
        if missing or extra:
            raise ValueError(f"{FILES[(k, split)]} and the dictionary disagree. "
                             f"Missing from file: {missing}. Not in dictionary: {extra}")
        if faults is not None:
            df = df[df["faultNumber"].isin(faults)]
        if runs is not None:
            df = df[df["simulationRun"].isin(list(runs))]
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)

    df = df.rename(columns=dict(zip(d.raw_name, d.name)))[list(d.name)]
    df["fault_number"] = df["fault_number"].astype(int)
    df["simulation_run"] = df["simulation_run"].astype(int)
    df["sample"] = df["sample"].astype(int)
    df["time_hours"] = (df["sample"] - 1) * MINUTES_PER_READING / 60.0
    return df, run_checks(df, split, len(d))


# ---------------------------------------------------------------- checks

def run_checks(df, split, n_dictionary_columns):
    key = ["fault_number", "simulation_run"]
    by_run = df.groupby(key)
    purge = [c for c in df.columns if c.startswith("purge_composition_")]
    product = [c for c in df.columns if c.startswith("product_composition_")]
    expected = READINGS_PER_RUN[split]
    over = int((df.groupby(key).reactor_pressure.max() > SHUTDOWN_KPA).sum())
    rows = [
        ("table has rows", len(df) > 0, f"{len(df):,} rows, {df.fault_number.nunique()} fault(s), "
                                         f"{by_run.ngroups} run(s)"),
        ("columns match the dictionary", df.shape[1] == n_dictionary_columns + 1, f"{n_dictionary_columns} + time_hours"),
        ("no missing values", int(df.isna().sum().sum()) == 0, f"{int(df.isna().sum().sum())} missing"),
        ("no repeated (fault, run, sample)", not df.duplicated(key + ["sample"]).any(), ""),
        ("samples increase within each run", bool(by_run["sample"].apply(lambda s: s.is_monotonic_increasing).all()), ""),
        (f"every run has {expected} readings ({split} set)", bool((by_run.size() == expected).all()),
         f"sizes seen: {sorted(int(n) for n in by_run.size().unique())}"),
        ("purge gas components A-H add up to about 100 mol %", bool(abs(df[purge].sum(axis=1).mean() - 100) < 1),
         f"mean {df[purge].sum(axis=1).mean():.2f}"),
    ]
    checks = pd.DataFrame(rows, columns=["check", "passed", "detail"])
    checks["passed"] = checks["passed"].map({True: "pass", False: "FAIL"})
    info = pd.DataFrame([
        ("product components D-H mean total (mol %)", "info", f"{df[product].sum(axis=1).mean():.2f}"),
        (f"runs with reactor pressure above {SHUTDOWN_KPA:.0f} kPa", "info", f"{over} of {by_run.ngroups}"),
    ], columns=["check", "passed", "detail"])
    return pd.concat([checks, info], ignore_index=True)


if __name__ == "__main__":
    table, checks = load_tep(kind="both", faults=[0, 2], runs=range(1, 11))
    print(checks.to_string(index=False))
