# Prompt: ask Claude for a data loader

Use this when you want Claude to write a loader for a data source. Fill in the brackets, attach your data dictionary, and send it. A filled-in example for the Tennessee Eastman data follows the template.

## Template

```
Write a Python data loader for [what the data is, in one sentence].

Where the data is
- Source: [web page, database, or folder path, and who runs it]
- Format: [CSV / Excel / R data file / database table / ...]
- Size: [number of files, rows, or GB, as far as you know]
- How I get it: [a download link, a login, or "I will put the files in a folder called data"]

My data dictionary is attached as a CSV. Its columns are raw_name, name, description, units,
type, and notes. The loader must use it to rename columns, and must stop with a clear message
if the file and the dictionary disagree about which columns exist.

What the loader returns
- One table with the dictionary's column names, plus [any column you want added, such as time in hours].
- Options to load only part of the data: [for example, by fault, date range, or site], because
  the full data is large.

Checks, run on every load and shown as a table with pass or FAIL
- [A fact you know is true of this data, e.g. every run has 500 readings]
- [Another, e.g. the values in a group of columns add up to about 100]
- [Another, e.g. no missing values, no repeated rows, time increases]

Rules
- Use only [Python standard library, pandas, and the one extra package the format needs].
- If the download fails, say so in plain words and say how to download the file by hand
  and where to put it; then use the files found there.
- Never fill in, drop, or change data without telling me.
- Build only this, with no extra features.

When you finish, tell me in a short list: (1) what you ran and what happened, (2) what you
could not run or test, and (3) anything about the source you assumed instead of confirmed.
```

## Why each part is there

- **What the data is and where it lives.** Claude can't see your systems. A vague source gets a plausible loader for a source that doesn't exist.
- **The dictionary.** Claude would otherwise guess what columns mean. The dictionary also makes the loader strict: if your file has a column the dictionary doesn't know, or the reverse, it stops instead of continuing with a wrong assumption.
- **Options to load part of the data.** Big sources need this. Without it the loader tries to pull everything, and a notebook can run out of memory.
- **Checks.** These are facts you know about the data. If the checks pass, the loader has read the data the way you understand it. If one fails, either the loader or the file is wrong, and you find out before you analyze anything. Pick checks that would fail for the mistake you worry about most.
- **The download fallback.** Downloads fail for reasons outside the code: a blocked site, a changed link, a login. A loader that explains how to download by hand keeps working.
- **"Tell me what you couldn't test."** Claude often can't reach the source from where it runs. Without this line, you get a confident summary of code that was never run against the real data. With it, you know exactly what to try first.

## Filled in: Tennessee Eastman Process

```
Write a Python data loader for the Tennessee Eastman Process simulation data, a chemical
plant simulation used to study process faults.

Where the data is
- Source: Harvard Dataverse, https://doi.org/10.7910/DVN/6C3JR1 (Rieth et al., 2017)
- Format: R data files, one data frame each: TEP_FaultFree_Training.RData,
  TEP_FaultFree_Testing.RData, TEP_Faulty_Training.RData, TEP_Faulty_Testing.RData
- Size: the faulty training file has 20 faults x 500 runs x 500 readings, about 5 million rows
- How I get it: download from the Dataverse page

My data dictionary is attached as a CSV (tep_data_dictionary.csv). Its columns are raw_name,
name, description, units, type, and notes. The loader must use it to rename columns, and must
stop with a clear message if the file and the dictionary disagree about which columns exist.

What the loader returns
- One table with the dictionary's column names, plus time_hours, where readings are 3 minutes apart.
- Options to choose fault-free data, faulty data, or both; training or testing; which fault
  numbers; and which run numbers, because the full data is large.

Checks, run on every load and shown as a table with pass or FAIL
- every run has 500 readings in the training set and 960 in the testing set
- the eight purge gas composition columns add up to about 100 mol %
- no missing values, no repeated (fault, run, sample), and samples increase within each run

Rules
- Use only the Python standard library, pandas, and pyreadr.
- If the download fails, say so in plain words and say how to download the file by hand
  and where to put it; then use the files found there.
- Never fill in, drop, or change data without telling me.
- Build only this, with no extra features.

When you finish, tell me in a short list: (1) what you ran and what happened, (2) what you
could not run or test, and (3) anything about the source you assumed instead of confirmed.
```

## Status of the example

The attached `tep_loader.py` was written to match this prompt. It was not generated from the prompt by a separate Claude session, so the prompt itself has not been tested the way the simulator prompt was. Claude's workspace could not reach the Harvard Dataverse server, so the real download and the reading of the R files have **not** been run. The renaming, checking, subsetting and download-error handling were tested on a real TEP file converted to the dataset's column names, and the download code was tested against a local stand-in server. Run it once on your own machine before relying on it.
