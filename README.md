# data-science-demos

Files that go with the blog series **Vibe coding for data science** ([blog.featuregraph.ai](https://blog.featuregraph.ai)).
The series shows people who work with data in Excel or Power BI, and have little or no Python, how to ask
Claude for the code and how to check what comes back.

Each folder holds the files for one post. Copy a folder, read its post, and follow along.

| Folder | What it is |
|---|---|
| [`tep_data_download`](tep_data_download) | Download the Tennessee Eastman Process simulation data, load it into a table with readable column names, check it, and plot it. |

## tep_data_download

The Tennessee Eastman Process (TEP) is a simulated chemical plant widely used to study process monitoring and
control. The data here is simulated, so results from it describe the simulation, not a real plant.

| File | What it does |
|---|---|
| `tep_loader.py` | Downloads the TEP files, renames the columns using the dictionary, adds a time column, and runs checks. |
| `tep_data_dictionary.csv` | One row per column: the name in the data file, the name to use, a description, units, and type. |
| `data_loader_prompt.md` | A fill-in prompt for asking Claude to write a loader like this one for your own data source, with the TEP version filled in as an example. |
| `plot.py` | Plotting helpers. `plot` stacks groups of columns from any table on shared axes. The two oscillation functions expect a table of detected oscillations with `oscillation_id`, `start_index`, `peak_index` and `end_index` columns. |

### Quick start

```python
from tep_loader import load_tep

df, checks = load_tep(kind="fault_free")
print(checks)
```

You need Python 3.10 or newer and `pip install pandas pyreadr matplotlib`. Keep `tep_loader.py` and
`tep_data_dictionary.csv` in the same folder as your notebook. The first call downloads the data into a
`tep_data` folder and reuses it afterwards.

`load_tep` returns the table and a check table showing pass or FAIL for each check. It takes these options:

| Option | Values |
|---|---|
| `kind` | `"fault_free"`, `"faulty"` or `"both"` |
| `split` | `"training"` (500 readings per run) or `"testing"` (960 readings per run) |
| `faults` | a list of fault numbers: 0 is no fault, 1 to 20 are the faults |
| `runs` | a list or range of run numbers, 1 to 500 |

The faulty training file has 20 faults x 500 runs x 500 readings, about 5 million rows. Load a few faults or
runs first (for example `faults=[2], runs=range(1, 11)`) unless you need all of it. Readings are 3 minutes apart,
and `time_hours` is the time since the start of a run.

### If something goes wrong

- **A 403 error from the server.** The loader sends its own identifier, because the server refuses Python's
  default one. If you still get a 403, change the `User-Agent` value in `HEADERS` at the top of `tep_loader.py`.
- **The file listing is refused.** Fill in `FILE_IDS` at the top of `tep_loader.py` with the numbers from the
  download links on the dataset page.
- **The download still fails.** Download the `.RData` files from the dataset page in your browser, put them in
  the `tep_data` folder, and run again. The loader uses any files it finds there.
- **`No module named pyreadr`.** Run `pip install pyreadr`.
- **A check says FAIL.** Do not analyze the data yet. Paste the check table into Claude, with what you
  were trying to load, and ask what could cause it.

### Data

The data is not stored in this repository. It comes from Harvard Dataverse: Rieth, C. A., Amsel, B. D., Tran, R.,
and Cook, M. B. (2017), *Additional Tennessee Eastman Process Simulation Data for Anomaly Detection Evaluation*,
[doi:10.7910/DVN/6C3JR1](https://doi.org/10.7910/DVN/6C3JR1). See the dataset page for its terms of use.

The dictionary uses the published TEP numbering: columns `xmeas_23` to `xmeas_28` are the reactor feed
composition, `xmeas_29` to `xmeas_36` the purge gas composition, and `xmeas_37` to `xmeas_41` the product
composition. Some copies of this data label those columns differently, and the loader's purge-gas check
(the eight purge columns should add up to about 100 mol %) is there to catch that.
