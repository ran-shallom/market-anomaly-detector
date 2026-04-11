# TODO

## 1. Automate IB Gateway launch via IBC

**Status:** Partially done — blocked on launch command

**Goal:** `./start.sh` should start IB Gateway automatically without the user needing to open it manually.

**What is already done:**
- IBC installed at `C:\IBC`
- `IBKR_USERNAME`, `IBKR_PASSWORD`, `IBC_PATH`, `IBC_WIN_PATH` added to `.env`
- `start.sh` generates `C:\IBC\config.ini` with credentials and IB Gateway path
- IBC script identified: `C:\IBC\Scripts\StartIBC.bat`
- IB Gateway version: `1045`, installed at `C:\Jts\ibgateway\1045`

**What is left:**
- Find a non-blocking way to launch `StartIBC.bat` from WSL
- Attempts so far:
  - `cmd.exe /c "start /min ..."` — blocked the script (did not return)
  - `powershell.exe Start-Process StartIBGateway.bat` — wrong script name
  - `powershell.exe Start-Process StartIBC.bat` — triggered Windows SmartScreen security warning
  - Added `Unblock-File` before launch — SmartScreen warning still appeared
  - Switched to `cmd.exe /c "start /min ..."` — blocked the terminal
- Next things to try:
  - Run `StartIBC.bat` via `setsid` or `nohup` to fully detach from WSL
  - Try: `nohup cmd.exe /c "C:\\IBC\\Scripts\\StartIBC.bat 1045" &>/dev/null &`
  - Or create a PowerShell wrapper script and call that instead of the .bat directly
  - Or use Windows Task Scheduler to trigger IBC on demand

**Current workaround:**
`start.sh` pauses and asks the user to open IB Gateway manually, then press Enter.

---

## 2. Extend anomaly detection to more symbols

**Status:** Not started

**Goal:** Allow the user to configure which symbols to monitor beyond the default 5 (AAPL, MSFT, GOOGL, AMZN, TSLA).

**Notes:**
- `SYMBOLS` list is already in `realtime/config.py` — easy to extend
- Each new symbol needs its own model trained on historical data
- Consider adding a simple UI in the dashboard to add/remove symbols

---

## 3. Improve the historical Word report

**Status:** Not started

**Goal:** The current `generate_report.py` is hardcoded to AAPL. Update it to generate a report for all monitored symbols using the live Parquet data.

**Notes:**
- Current report is at `results/AAPL_Anomaly_Report.docx`
- Should read from `realtime/data/` instead of the batch CSV
- Could be triggered automatically after nightly retrain

---

## 4. Desktop notifications on Windows (WSL limitation)

**Status:** Known limitation

**Goal:** Desktop popup alerts currently fail in WSL because there is no desktop notification system in Linux.

**Notes:**
- Telegram alerts work fine as a replacement
- To fix: run the alert service natively on Windows instead of WSL
- Or use `powershell.exe` to trigger a Windows toast notification from WSL:
  ```bash
  powershell.exe -Command "
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show('Anomaly detected: AAPL')
  "
  ```
