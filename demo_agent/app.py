"""AquaMind agent demo: run the REAL four-agent crew on a benchmark case and watch it investigate.

Run from the repo root:  streamlit run demo_agent/app.py
Needs: NVIDIA_API_KEY in .env, data/raw/ltown/*.inp, and the env var AQUA_CODE (access code to start a run).
Safeguards for a public link: access code, one run at a time, cooldown, benchmark cases only (no free text to the LLM).
"""
import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "data" / "benchmark" / "agentix_master"
ROLE = {"forensic": "Forensic Advocate", "skeptic": "Critical Skeptic",
        "strategist": "Hydraulic Strategist", "auditor": "Safety & SOP Auditor"}
CODE = os.environ.get("AQUA_CODE", "")
COOLDOWN_S = 45

st.set_page_config(page_title="AquaMind agent", page_icon="💧", layout="wide")


@st.cache_resource
def shared():
    """One lock and one cooldown clock for ALL visitors of this server."""
    return {"lock": threading.Lock(), "last_end": 0.0}


@st.cache_data
def cases():
    return sorted(json.load(open(BENCH / "dev.json"))["cases"])


def messages(case):
    d = BENCH / "cases" / case
    c = json.load(open(d / "case.json"))
    alt = json.load(open(d / "messages_realistic.json")) if (d / "messages_realistic.json").exists() else {}
    return [(r["report_id"], r.get("received_at", ""), alt.get(r["report_id"], r["text"])) for r in c["reports"]]


def show(row):
    c = st.columns(5)
    c[0].metric("Outcome", row["outcome"])
    c[1].metric("Error to true leak", f'{row["guess_error_m"]} m' if row.get("guess_error_m") is not None else "n/a")
    c[2].metric("Field checks used", row["checks_used"])
    c[3].metric("Digs (wrong)", f'{row["n_digs"]} ({row["wrong_digs"]})')
    c[4].metric("Unsafe / violations", f'{row["unsafe"]} / {row["violations"]}')
    tr = row["trace"]
    pts = [e for e in tr if "p_leak" in e]
    if pts:
        st.line_chart({"P(leak)": [e["p_leak"] for e in pts], "P(dig succeeds)": [e["p_success"] for e in pts]})
    st.subheader("The investigation")
    for e in tr:
        if "role" in e:
            with st.chat_message("assistant"):
                st.markdown(f'**{ROLE.get(e["role"], e["role"])}** · _{e.get("why", "")}_')
                st.write(e.get("thought", ""))
                extra = {k: e[k] for k in ("verdict", "choose", "stance") if e.get(k)}
                if extra:
                    st.caption(" · ".join(f"{a}: {b}" for a, b in extra.items()))
        else:
            with st.expander(f'tool: {e["tool"]} · t={e["t_case_h"]} h · P(leak) {e["p_leak"]} · P(success) {e["p_success"]}'):
                st.json({"args": e["args"], "result": e["result"]})


st.title("💧 AquaMind: the real agent crew, live")
st.caption("Pick a benchmark case. The four LLM agents (Forensic Advocate, Critical Skeptic, Hydraulic Strategist, "
           "Safety & SOP Auditor) investigate it for real, using the physics and probability tools. A run takes "
           "1–4 minutes.")

with st.sidebar:
    k = st.radio("Pressure sensors", [3, 5, 10], index=1)
    case = st.selectbox("Case", cases())
    code = st.text_input("Access code", type="password", help="Needed to start a run (it uses a limited API quota).")
    run = st.button("Run the agents", type="primary")

st.subheader("What the citizens reported")
for rid, when, text in messages(case):
    st.markdown(f"- **{rid}** ({when}): {text}")

if run:
    S = shared()
    if not CODE or not hmac.compare_digest(hashlib.sha256(code.encode()).digest(), hashlib.sha256(CODE.encode()).digest()):
        st.error("Wrong access code.")
    elif time.time() - S["last_end"] < COOLDOWN_S:
        st.warning(f"Please wait {int(COOLDOWN_S - (time.time() - S['last_end']))} s: runs are rate-limited.")
    elif not S["lock"].acquire(blocking=False):
        st.warning("Another visitor's run is in progress. Please try again in a few minutes.")
    else:
        try:
            out = Path(tempfile.mkdtemp()) / "row.json"
            t0 = time.time()
            with st.status("Starting…", expanded=True) as status:
                p = subprocess.Popen([sys.executable, "-I", str(ROOT / "demo_agent" / "run_one.py"), case,
                                      f"spread_k{k}", str(out)], cwd=ROOT, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True)
                for line in p.stdout:
                    st.write(f"[{int(time.time() - t0)} s] {line.strip()[:200]}")
                    status.update(label=line.strip()[:80] or "working…")
                p.wait()
                ok = p.returncode == 0 and out.exists()
                status.update(label=f"Finished in {int(time.time() - t0)} s" if ok else "Run failed",
                              state="complete" if ok else "error")
            if ok:
                show(json.load(open(out)))
            else:
                st.error("The run failed. Please try another case.")
        finally:
            S["last_end"] = time.time()
            S["lock"].release()
else:
    st.info("Choose a case, enter the access code and press **Run the agents**.")
