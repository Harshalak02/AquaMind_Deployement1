"""AquaMind replay demo: step through recorded crew investigations (no API keys or models needed)."""
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs" / "evaluation" / "agentix" / "crew"
ROLE = {"forensic": "Forensic Advocate", "skeptic": "Critical Skeptic",
        "strategist": "Hydraulic Strategist", "auditor": "Safety & SOP Auditor"}

st.set_page_config(page_title="AquaMind demo", page_icon="💧", layout="wide")


@st.cache_data
def load(k):
    d = LOGS / f"k{k}"
    rows = {}
    for l in open(next(d.glob("*_agentix_crew.jsonl"))):
        r = json.loads(l)
        rows[r["case"]] = r
    trace = {}
    for l in open(next(d.glob("*_trace.jsonl"))):
        r = json.loads(l)
        trace.setdefault(r["case"], []).append(r)
    return rows, trace


st.title("💧 AquaMind: replay of a leak investigation")
st.caption("Sparse sensors + citizen messages + a four-agent crew. This page replays recorded runs from the "
           "evaluation logs; nothing is computed live.")

with st.sidebar:
    k = st.radio("Pressure sensors", [3, 5, 10], index=1)
    rows, trace = load(k)
    only = st.selectbox("Show", ["all cases", "leak found", "leak not found"])
    names = sorted(c for c, r in rows.items()
                   if only == "all cases" or (r.get("found") == (only == "leak found")))
    case = st.selectbox("Case", names)

row, events = rows[case], trace[case]
c = st.columns(5)
c[0].metric("Outcome", row["outcome"])
c[1].metric("Error to true leak", f'{row["guess_error_m"]} m' if row.get("guess_error_m") is not None else "n/a")
c[2].metric("Field checks used", row["checks_used"])
c[3].metric("Digs (wrong)", f'{row["n_digs"]} ({row["wrong_digs"]})')
c[4].metric("Unsafe / rule violations", f'{row["unsafe"]} / {row["violations"]}')
st.info("**Key actions:** " + row["key_action"])

st.line_chart({"P(leak)": [e["p_leak"] for e in events if "p_leak" in e],
               "P(dig succeeds)": [e["p_success"] for e in events if "p_success" in e]})

n = st.slider("Step through the investigation", 1, len(events), len(events))
for e in events[:n]:
    if e["kind"] == "llm_turn":
        with st.chat_message("assistant"):
            st.markdown(f'**{ROLE.get(e["role"], e["role"])}** · _{e.get("why", "")}_')
            st.write(e.get("thought", ""))
            extra = {x: e[x] for x in ("verdict", "choose", "stance") if e.get(x)}
            if extra:
                st.caption(" · ".join(f"{a}: {b}" for a, b in extra.items()))
    else:
        with st.expander(f'step {e["step"]} · t={e["t_case_h"]} h · tool: {e["tool"]} '
                         f'· P(leak) {e["p_leak"]} · P(success) {e["p_success"]}'):
            st.json({"args": e["args"], "result": e["result"]})
