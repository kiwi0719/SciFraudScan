from __future__ import annotations

from io import BytesIO
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from research_integrity_screen.pipeline import scan_dataframe
from research_integrity_screen.reporting import finding_detail_lines

app = FastAPI(title="SciFraudScan")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _HTML


@app.post("/api/scan")
async def scan(
    data: Annotated[UploadFile, File()],
) -> dict[str, object]:
    try:
        df = await _read_csv(data)
    except pd.errors.ParserError as exc:
        raise HTTPException(status_code=400, detail=f"CSV parse failed: {exc}") from exc

    report = scan_dataframe(df)
    for section in report["sections"]:
        for finding in section["findings"]:
            finding["detail_lines"] = finding_detail_lines(finding)
    return report


def main() -> None:
    import uvicorn

    uvicorn.run("research_integrity_screen.web:app", host="127.0.0.1", port=8765, reload=False)


async def _read_csv(file: UploadFile | None) -> pd.DataFrame:
    if file is None:
        raise HTTPException(status_code=400, detail="Missing CSV file.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"{file.filename or 'CSV'} is empty.")
    return pd.read_csv(BytesIO(content))


_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SciFraudScan</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #667085;
      --line: #d7dde5;
      --panel: #ffffff;
      --bg: #f4f7f9;
      --pass: #1f7a4d;
      --warn: #9a5b00;
      --risk: #b42318;
      --brand: #1d4f91;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }
    h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }
    p { margin: 0; color: var(--muted); line-height: 1.55; }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      gap: 20px;
      padding: 20px 32px 32px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    form.panel { padding: 18px; align-self: start; position: sticky; top: 16px; }
    label { display: block; font-weight: 650; font-size: 13px; margin: 14px 0 6px; }
    input[type="file"], input[type="text"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fff;
      color: var(--ink);
      font-size: 14px;
    }
    button {
      width: 100%;
      margin-top: 18px;
      border: 0;
      border-radius: 6px;
      padding: 11px 14px;
      background: var(--brand);
      color: white;
      font-weight: 700;
      cursor: pointer;
    }
    button:disabled { opacity: .65; cursor: wait; }
    .hint { margin-top: 10px; font-size: 13px; }
    .detected { padding: 14px 16px; margin-bottom: 14px; }
    .detected h2 { margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }
    .detected ul { margin-top: 0; }
    .summary {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .metric { padding: 16px; }
    .metric span { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }
    .metric strong { display: block; margin-top: 6px; font-size: 24px; }
    .section { margin-bottom: 14px; overflow: hidden; }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
    }
    .section h2 { margin: 0; font-size: 17px; letter-spacing: 0; }
    .finding { padding: 14px 16px; border-bottom: 1px solid var(--line); }
    .finding:last-child { border-bottom: 0; }
    .finding-title { display: flex; gap: 10px; align-items: center; justify-content: space-between; }
    .finding-title h3 { margin: 0; font-size: 15px; letter-spacing: 0; }
    .badge { border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 750; white-space: nowrap; }
    .Pass { color: var(--pass); background: #e8f5ee; }
    .Warning { color: var(--warn); background: #fff4df; }
    .High-Risk { color: var(--risk); background: #ffe9e7; }
    .finding p { margin-top: 8px; font-size: 14px; }
    ul { margin: 10px 0 0; padding-left: 18px; color: #344054; font-size: 13px; line-height: 1.55; }
    .empty { padding: 32px; text-align: center; color: var(--muted); }
    .error { color: var(--risk); margin-top: 12px; font-size: 14px; }
    @media (max-width: 860px) {
      main { grid-template-columns: 1fr; padding: 16px; }
      header { padding: 22px 16px 14px; }
      form.panel { position: static; }
      .summary { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>SciFraudScan</h1>
    <p>Upload one CSV. SciFraudScan automatically detects numeric data, group columns, time columns, p-values, and reported statistics where possible.</p>
  </header>
  <main>
    <form id="scan-form" class="panel">
      <label for="data">Dataset CSV</label>
      <input id="data" name="data" type="file" accept=".csv,text/csv" required>
      <p class="hint">No column mapping is required. The scanner infers usable checks from the file.</p>
      <button id="scan-button" type="submit">Scan</button>
      <div id="error" class="error"></div>
    </form>
    <section id="results">
      <div class="panel empty">Upload any CSV to see automatically selected checks and specific abnormal indicators.</div>
    </section>
  </main>
  <script>
    const form = document.getElementById("scan-form");
    const button = document.getElementById("scan-button");
    const errorBox = document.getElementById("error");
    const results = document.getElementById("results");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      errorBox.textContent = "";
      button.disabled = true;
      button.textContent = "Scanning";
      try {
        const response = await fetch("/api/scan", { method: "POST", body: new FormData(form) });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Scan failed");
        render(payload);
      } catch (error) {
        errorBox.textContent = error.message;
      } finally {
        button.disabled = false;
        button.textContent = "Scan";
      }
    });

    function render(report) {
      results.innerHTML = "";
      const summary = document.createElement("div");
      summary.className = "summary";
      summary.append(metric("Score", `${report.research_integrity_score} / 100`));
      summary.append(metric("Overall Risk", report.overall_risk));
      summary.append(metric("Sections", report.sections.length));
      results.append(summary);
      results.append(autoDetection(report.auto_detection || {}));
      for (const section of report.sections) {
        const panel = document.createElement("article");
        panel.className = "panel section";
        panel.innerHTML = `
          <div class="section-header">
            <h2>${escapeHtml(section.name)}</h2>
            <span class="badge ${badgeClass(section.status)}">${escapeHtml(section.status)} · ${section.score}</span>
          </div>`;
        for (const finding of section.findings) {
          const div = document.createElement("div");
          div.className = "finding";
          div.innerHTML = `
            <div class="finding-title">
              <h3>${escapeHtml(finding.check)}</h3>
              <span class="badge ${badgeClass(finding.status)}">${escapeHtml(finding.status)} · ${finding.score}</span>
            </div>
            <p>${escapeHtml(finding.message)}</p>
            ${detailList(finding.detail_lines || [])}`;
          panel.append(div);
        }
        results.append(panel);
      }
    }

    function metric(label, value) {
      const div = document.createElement("div");
      div.className = "panel metric";
      div.innerHTML = `<span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong>`;
      return div;
    }

    function autoDetection(auto) {
      const div = document.createElement("div");
      div.className = "panel detected";
      const notes = auto.notes || [];
      const lines = notes.length ? notes : ["No group, time, p-value, or reported-statistics columns were detected; numeric dataset checks were still run."];
      div.innerHTML = `<h2>Auto-detected inputs</h2><ul>${lines.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
      return div;
    }

    function detailList(lines) {
      if (!lines.length) return "";
      return `<ul>${lines.map(line => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
    }

    function badgeClass(status) {
      return String(status).replace(/\\s+/g, "-");
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
