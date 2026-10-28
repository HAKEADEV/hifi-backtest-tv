@echo off
REM Example only. Adjust TDS path, symbol, range, export format name and output folder.
set TDS="C:\Program Files (x86)\Tick Data Suite\TickDataSuite.exe"
set SYM=EURUSD
set RANGE=2019.01.01-2019.12.31
set FMT=MyBars
set OUT=C:\hifi\%SYM%.csv
%TDS% /download:Dukascopy:%SYM%
%TDS% /export:Dukascopy:%SYM%:%RANGE% /eformat:%FMT% /output:%OUT%
echo Exported to %OUT%
