# Optional: Tick Data Suite (Windows, paid)

Only needed if you want to compare against an MT4/MT5 setup using Tick Data Suite (TDS).
TDS is a **paid, Windows-only** product; HiFi does not ship or redistribute any TDS data.

## Command line (documented TDS CLI)
`tds_export.bat` downloads and exports with the TDS command line, e.g.
```
TickDataSuite.exe /download:Dukascopy:EURUSD
TickDataSuite.exe /export:Dukascopy:EURUSD:2019.01.01-2019.12.31 /eformat:MyBars /output:C:\hifi\EURUSD.csv
```
- The export format (`/eformat:` → a `.tcf`/`.bcf` custom format) must first be created **in the TDS GUI**
  (Export → custom CSV format). Pick a GMT offset (0, +2, or NY+7 "DST US") and remember it.
- Check the exact switches against your TDS version's help; paths depend on your install.

## Loading into HiFi
```yaml
feeds:
  reference: {type: tds, path: "C:/hifi/EURUSD.csv",
              columns: [date, time, open, high, low, close, volume], sep: ",", server_tz: "NY+7"}
```
`columns` names each column in order (`datetime` for one combined column, `_` to skip);
`header: 0` if the file has a header row; `time_format` for unusual formats.
