import streamlit as st
import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import json
import html as html_lib

# ── Config ──────────────────────────────────────────────────────────────────
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
BASE_ID = "appGHHBqsuh7XsRsk"
EVENTS_TABLE     = "tblqwVuM9WqAE1SdO"
ATTENDANCE_TABLE = "tblUcdGlCHRKVL5Dl"
PEOPLE_TABLE     = "tblf121u7j3qgoPxi"
CHANNELS_TABLE   = "tblngNG8Bz7Tb8Mjt"
SEATING_URL      = "https://posit-connect.prod.netflix.net/content/8133e8a9-955c-44c0-9498-e5c70b184c03/"

RED   = "#E50915"
GOLD  = "#DFB864"
SKY   = "#8FC2E6"
BG    = "#181616"

st.set_page_config(
    page_title="Netflix Ads Marketing Project Hub",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dark theme ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  .stApp {{ background:{BG}; color:#DCE4C2; }}
  .stApp .stMetric {{ background:#1f1c1c; border:1px solid #3a3434; border-radius:8px; padding:10px 14px; }}
  .stApp .stMetricLabel {{ font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:#a09888; }}
  .stApp .stMetricValue {{ font-size:22px; font-weight:800; color:#DCE4C2; }}
  div[data-testid="stTabs"] button[role="tab"] {{
    font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.3px;
    color:#6b6060; border-bottom:2px solid transparent; padding:9px 14px;
  }}
  div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color:#DCE4C2; border-bottom:2px solid {RED};
  }}
  footer {{ visibility:hidden; }}
  #MainMenu {{ visibility:hidden; }}
  .event-card {{
    background:#1f1c1c; border:1px solid #3a3434; border-radius:12px;
    padding:16px 18px; margin-bottom:10px; position:relative; overflow:hidden;
  }}
  .ev-accent-top {{ position:absolute; top:0; left:0; right:0; height:2px; }}
  .ev-name {{ font-size:15px; font-weight:800; color:#DCE4C2; }}
  .ev-meta {{ font-size:12px; color:#a09888; margin-top:2px; }}
  .stat-row {{ display:flex; gap:16px; flex-wrap:wrap; margin-top:12px; }}
  .stat-item {{ }}
  .stat-lbl {{ font-size:9px; color:#a09888; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }}
  .stat-val {{ font-size:18px; font-weight:800; color:#DCE4C2; }}
  .gold-lbl {{ font-size:10px; font-weight:800; text-transform:uppercase;
               letter-spacing:2px; color:{GOLD}; margin-bottom:12px; }}
  .rm-wrap {{ overflow-x:auto; margin-bottom:16px; }}
  .rm-inner {{ min-width:600px; }}
  .rm-months {{ display:grid; grid-template-columns:80px repeat(12,1fr);
                font-size:9px; color:#6b6060; font-weight:700; text-align:center;
                text-transform:uppercase; letter-spacing:.04em; padding-bottom:4px; }}
  .rm-row {{ display:flex; margin-bottom:5px; align-items:stretch; }}
  .rm-lbl {{ width:80px; flex-shrink:0; font-size:11px; font-weight:700; color:#DCE4C2;
             padding-right:8px; display:flex; align-items:center; }}
  .rm-track {{ display:grid; grid-template-columns:repeat(12,1fr); flex:1;
               gap:1px; background:#3a3434; border-radius:4px; overflow:hidden;
               min-height:26px; }}
  .rm-cell {{ background:#2a2626; padding:2px 3px; min-height:26px; }}
  .rm-pill {{ display:block; width:100%; border-radius:3px; padding:2px 4px;
              font-size:9px; font-weight:700; white-space:nowrap; overflow:hidden;
              text-overflow:ellipsis; margin-bottom:2px; cursor:default; line-height:1.5; }}
  .res-section {{ background:#1f1c1c; border:1px solid #3a3434; border-radius:12px;
                  padding:16px 18px; margin-top:16px; }}
  .note-box {{ background:#2a2626; border-left:3px solid {GOLD}; padding:8px 12px;
               font-size:12px; color:#a09888; margin-bottom:12px;
               border-radius:0 8px 8px 0; }}
  .bot-box {{ background:#2a2626; border:1px solid #3a3434; border-radius:12px;
              padding:12px 14px; margin-bottom:12px; }}
</style>
""", unsafe_allow_html=True)


# ── Airtable helpers ─────────────────────────────────────────────────────────
def airtable_get(table_id, params=None):
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}"
    records, offset = [], None
    while True:
        p = params.copy() if params else {}
        if offset:
            p["offset"] = offset
        resp = requests.get(url, headers=headers, params=p, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def airtable_patch(table_id, record_id, fields):
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_id}/{record_id}"
    resp = requests.patch(url, headers=headers, json={"fields": fields}, timeout=15)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=120, show_spinner=False)
def load_events():
    raw = airtable_get(EVENTS_TABLE)
    today = date.today()
    rows = []
    for r in raw:
        f = r["fields"]
        ev_date_str = f.get("Event Date", "")
        try:
            ev_date = datetime.strptime(ev_date_str, "%Y-%m-%d").date() if ev_date_str else None
        except Exception:
            ev_date = None

        # Only include upcoming or no-date events
        if ev_date and ev_date < today:
            is_past = True
        else:
            is_past = False

        inv   = int(f.get("Total Invited") or 0)
        con   = int(f.get("Total Confirmed") or 0)
        dec   = int(f.get("Total Declined") or 0)
        att   = int(f.get("Total Attended") or 0)
        nos   = int(f.get("Total No Shows") or 0)
        pnd   = max(0, inv - con - dec)

        region_raw = f.get("Region (from Project)")
        if isinstance(region_raw, dict):
            regions = [v["name"] for v in region_raw.get("valuesByLinkedRecordId", {}).values() for v in v]
        else:
            regions = []
        global_raw = f.get("Global (from Project)")
        if isinstance(global_raw, dict):
            global_vals = list(global_raw.get("valuesByLinkedRecordId", {}).values())
            is_global = any("Global" in str(v) for v in global_vals)
        else:
            is_global = False

        campaign_raw = f.get("Parent Campaign ID (from Project)")
        campaign = ""
        if isinstance(campaign_raw, dict):
            vals = list(campaign_raw.get("valuesByLinkedRecordId", {}).values())
            if vals and vals[0]:
                campaign = vals[0][0] if isinstance(vals[0], list) else str(vals[0])

        rows.append({
            "id":          r["id"],
            "name":        f.get("Name", "Unnamed Event"),
            "status":      (f.get("Status") or {}).get("name", "") if isinstance(f.get("Status"), dict) else f.get("Status", ""),
            "event_date":  ev_date_str,
            "ev_date_obj": ev_date,
            "is_past":     is_past,
            "splash_url":  f.get("Splash Event URL", ""),
            "total_invited":   inv,
            "total_confirmed": con,
            "total_declined":  dec,
            "total_attended":  att,
            "total_no_shows":  nos,
            "total_pending":   pnd,
            "pct_rsvp_yes": round(con/inv*100) if inv else 0,
            "pct_pending":  round(pnd/inv*100) if inv else 0,
            "layout_json":  f.get("Seating Layout JSON", ""),
            "regions":     regions,
            "is_global":   is_global,
            "campaign":    campaign,
        })
    return rows


@st.cache_data(ttl=120, show_spinner=False)
def load_attendance(event_record_id: str):
    raw = airtable_get(
        ATTENDANCE_TABLE,
        params={
            "filterByFormula": f"FIND('{event_record_id}', ARRAYJOIN({{Event}}, ','))",
            "fields[]": [
                "Full Name", "Email", "Title", "Company",
                "RSVP Status", "Registration Date", "Seniority",
                "Event and Status",
            ],
        },
    )
    rows = []
    for r in raw:
        f = r["fields"]
        rsvp = f.get("RSVP Status")
        if isinstance(rsvp, dict):
            rsvp = rsvp.get("name", "")
        seniority = f.get("Seniority")
        if isinstance(seniority, dict):
            vals = list(seniority.get("valuesByLinkedRecordId", {}).values())
            seniority = vals[0][0] if vals and vals[0] else ""
        elif isinstance(seniority, list):
            seniority = seniority[0] if seniority else ""

        reg_raw = f.get("Registration Date", "")
        try:
            reg_dt = datetime.fromisoformat(reg_raw.replace("Z", "+00:00"))
            reg_str = reg_dt.strftime("%-m/%-d/%Y %-I:%M%p").lower()
        except Exception:
            reg_str = reg_raw

        rows.append({
            "Full Name":       f.get("Full Name", "").strip(),
            "Email":           f.get("Email", ""),
            "Title":           f.get("Title", ""),
            "Company":         f.get("Company", ""),
            "RSVP Status":     rsvp or "",
            "Registration Date": reg_str,
            "Seniority":       seniority or "",
            "Event and Status": f.get("Event and Status", ""),
        })
    return rows


@st.cache_data(ttl=300, show_spinner=False)
def load_people_linkedin():
    """Build email→LinkedIn lookup from People table."""
    raw = airtable_get(PEOPLE_TABLE, params={"fields[]": ["Email", "LinkedIn URL (Source)"]})
    lookup = {}
    for r in raw:
        f = r["fields"]
        email = f.get("Email", "")
        li = f.get("LinkedIn URL (Source)", "")
        if email and li:
            lookup[email.lower()] = li
    return lookup


@st.cache_data(ttl=120, show_spinner=False)
def load_channels():
    raw = airtable_get(CHANNELS_TABLE)
    today = date.today()
    rows = []
    for r in raw:
        f = r["fields"]
        planned = f.get("Planned Launch Date", "")
        try:
            planned_date = datetime.strptime(planned, "%Y-%m-%d").date() if planned else None
        except Exception:
            planned_date = None

        themes_raw = f.get("Content Theme(s)", [])
        themes = [t.get("name", t) if isinstance(t, dict) else t for t in themes_raw] if isinstance(themes_raw, list) else []

        project_raw = f.get("All Projects", [])
        project_name = project_raw[0].get("name", "") if project_raw else ""

        campaign_id = ""
        camp_raw = f.get("Parent Campaign ID (from All Projects)")
        if isinstance(camp_raw, dict):
            vals = list(camp_raw.get("valuesByLinkedRecordId", {}).values())
            if vals and vals[0]:
                campaign_id = vals[0][0] if isinstance(vals[0], list) else str(vals[0])

        # Parse region from campaign ID prefix
        region = "UNKNOWN"
        if "[GLOBAL" in campaign_id.upper():
            region = "GLOBAL"
        elif "[UCAN" in campaign_id.upper():
            region = "UCAN"
        elif "[LATAM" in campaign_id.upper():
            region = "LATAM"
        elif "[APAC" in campaign_id.upper():
            region = "APAC"
        elif "[EMEA" in campaign_id.upper():
            region = "EMEA"

        ch_type = (f.get("Channel Dropdown") or {}).get("name", "") if isinstance(f.get("Channel Dropdown"), dict) else ""

        rows.append({
            "id":           r["id"],
            "name":         f.get("Channel", "Untitled"),
            "type":         ch_type,
            "planned_date": planned,
            "planned_obj":  planned_date,
            "is_future":    bool(planned_date and planned_date >= today),
            "project":      project_name,
            "campaign_id":  campaign_id,
            "region":       region,
            "themes":       themes,
            "status":       (f.get("Status") or {}).get("name", "") if isinstance(f.get("Status"), dict) else "",
        })
    return rows


def pct_str(val, total):
    if not total:
        return "—"
    return f"{round(val/total*100)}%"


def roadmap_html(rows_data):
    """Render a 12-month roadmap as HTML."""
    html = '<div class="rm-wrap"><div class="rm-inner">'
    html += '<div class="rm-months"><div></div>'
    for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]:
        html += f"<div>{m}</div>"
    html += "</div>"
    for label, items, color, text_color in rows_data:
        html += f'<div class="rm-row"><div class="rm-lbl">{label}</div><div class="rm-track">'
        for mi in range(1, 13):
            cell_items = [x for x in items if x.get("month") == mi]
            html += '<div class="rm-cell">'
            for item in cell_items:
                html += f'<span class="rm-pill" style="background:{color};color:{text_color}">{item["name"]}</span>'
            html += "</div>"
        html += "</div></div>"
    html += "</div></div>"
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  APP LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

# Header
col_n, col_title, col_seat = st.columns([1, 10, 3])
with col_n:
    st.markdown(f'<div style="background:{RED};width:36px;height:36px;border-radius:6px;display:flex;align-items:center;justify-content:center;margin-top:6px"><span style="color:white;font-weight:900;font-size:17px">N</span></div>', unsafe_allow_html=True)
with col_title:
    st.markdown('<h1 style="margin:0;padding:0;font-size:22px;font-weight:900;color:#DCE4C2;letter-spacing:-0.5px">Netflix Ads Marketing Project Hub</h1>', unsafe_allow_html=True)
with col_seat:
    st.markdown(f'<div style="text-align:right;padding-top:6px"><a href="{SEATING_URL}" target="_blank" style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;background:linear-gradient(135deg,{RED},#730011);color:white;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none;letter-spacing:.3px">🪑 Seating Studio ↗</a></div>', unsafe_allow_html=True)

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.markdown(f"<div style='height:2px;background:linear-gradient(90deg,{RED},#f66c07,{GOLD},transparent);margin-bottom:12px'></div>", unsafe_allow_html=True)

tab_hub, tab_detail, tab_people, tab_channels = st.tabs(["Events Hub", "Event Detail", "People", "Channel Hub"])

events = load_events()
upcoming = [e for e in events if not e["is_past"]]


# ════════════════════════════════════════════════════════════════════════════
#  TAB 1 — EVENTS HUB
# ════════════════════════════════════════════════════════════════════════════
with tab_hub:
    st.markdown('<div class="gold-lbl">Upcoming events</div>', unsafe_allow_html=True)

    total_inv  = sum(e["total_invited"]   for e in upcoming)
    total_yes  = sum(e["total_confirmed"] for e in upcoming)
    total_no   = sum(e["total_declined"]  for e in upcoming)
    total_att  = sum(e["total_attended"]  for e in upcoming)
    total_nos  = sum(e["total_no_shows"]  for e in upcoming)
    total_pnd  = sum(e["total_pending"]   for e in upcoming)

    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)
    k1.metric("Upcoming events",   len(upcoming))
    k2.metric("Invited",           f"{total_inv:,}")
    k3.metric("RSVP Yes",          f"{total_yes:,}")
    k4.metric("RSVP No",           f"{total_no:,}")
    k5.metric("Pending",           f"{total_pnd:,}")
    k6.metric("Attended",          f"{total_att:,}")
    k7.metric("No Show",           f"{total_nos:,}")
    k8.metric("% RSVP Yes",        pct_str(total_yes, total_inv))

    # Roadmap
    st.markdown('<div class="gold-lbl" style="margin-top:16px">2026 event roadmap — region from Airtable fields</div>', unsafe_allow_html=True)

    # Build roadmap data by region/global
    roadmap_rows = {}
    for ev in upcoming:
        row_key = "Global" if ev["is_global"] else (ev["regions"][0] if ev["regions"] else "Other")
        if row_key not in roadmap_rows:
            roadmap_rows[row_key] = []
        ev_date_str = ev["event_date"]
        month = None
        if ev_date_str:
            try:
                month = datetime.strptime(ev_date_str, "%Y-%m-%d").month
            except Exception:
                pass
        roadmap_rows[row_key].append({"name": ev["name"], "month": month})

    REGION_COLORS = {"Global": ("rgba(143,194,230,.2)", SKY), "APAC": ("rgba(34,197,94,.2)", "#4ade80"),
                     "LATAM": ("rgba(229,9,20,.15)", "#ff6b6b"), "EMEA": ("rgba(223,184,100,.2)", GOLD),
                     "UCAN": ("rgba(139,92,246,.2)", "#a78bfa")}

    rm_html = '<div class="rm-wrap"><div class="rm-inner">'
    rm_html += '<div class="rm-months"><div></div>'
    for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]:
        rm_html += f"<div>{m}</div>"
    rm_html += "</div>"
    for region, items in roadmap_rows.items():
        bg, tc = REGION_COLORS.get(region, ("rgba(107,114,128,.2)", "#9ca3af"))
        rm_html += f'<div class="rm-row"><div class="rm-lbl">{region}</div><div class="rm-track">'
        for mi in range(1, 13):
            cell = [x for x in items if x["month"] == mi]
            rm_html += "<div class=\"rm-cell\">"
            for item in cell:
                rm_html += f'<span class="rm-pill" style="background:{bg};color:{tc}">{html_lib.escape(item["name"])}</span>'
            rm_html += "</div>"
        rm_html += "</div></div>"
    rm_html += "</div></div>"
    st.markdown(rm_html, unsafe_allow_html=True)

    # Event cards
    st.markdown('<div class="gold-lbl">Upcoming events</div>', unsafe_allow_html=True)

    for ev in upcoming:
        region_label = "Global" if ev["is_global"] else (ev["regions"][0] if ev["regions"] else "")
        accent_bg, accent_tc = REGION_COLORS.get(region_label, ("rgba(107,114,128,.2)", "#9ca3af"))
        accent_line = f"linear-gradient(90deg,{accent_tc},{accent_tc}88)"

        date_str = ""
        if ev["event_date"]:
            try:
                date_str = datetime.strptime(ev["event_date"], "%Y-%m-%d").strftime("%B %-d, %Y")
            except Exception:
                date_str = ev["event_date"]

        splash_link = f'<a href="{ev["splash_url"]}" target="_blank" style="font-size:11px;color:{SKY};text-decoration:none">↗ Splash</a>' if ev["splash_url"] else ""

        inv = ev["total_invited"]; yes = ev["total_confirmed"]; no = ev["total_declined"]
        pnd = ev["total_pending"]; att = ev["total_attended"]; nos = ev["total_no_shows"]
        pct_yes = pct_str(yes, inv); pct_pnd = pct_str(pnd, inv)

        st.markdown(f"""
        <div class="event-card">
          <div class="ev-accent-top" style="background:{accent_line}"></div>
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
              <div class="ev-name">{html_lib.escape(ev['name'])}</div>
              <div class="ev-meta">{f'📅 {date_str} &nbsp;·&nbsp;' if date_str else '📅 Date TBD &nbsp;·&nbsp;'} {html_lib.escape(ev.get('campaign','') or '')}</div>
            </div>
            <div style="text-align:right">
              <span style="background:{accent_bg};color:{accent_tc};padding:2px 8px;border-radius:99px;font-size:10px;font-weight:800;text-transform:uppercase">{region_label}</span>
              {('<br>' + splash_link) if splash_link else ''}
            </div>
          </div>
          <div class="stat-row">
            <div class="stat-item"><div class="stat-lbl">Invited</div><div class="stat-val">{inv:,}</div></div>
            <div class="stat-item"><div class="stat-lbl">RSVP Yes</div><div class="stat-val" style="color:{RED}">{yes:,}</div></div>
            <div class="stat-item"><div class="stat-lbl">RSVP No</div><div class="stat-val">{no:,}</div></div>
            <div class="stat-item"><div class="stat-lbl">Pending</div><div class="stat-val" style="color:{GOLD}">{pnd:,}</div></div>
            <div class="stat-item"><div class="stat-lbl">Attended</div><div class="stat-val">{att:,}</div></div>
            <div class="stat-item"><div class="stat-lbl">No Show</div><div class="stat-val">{nos:,}</div></div>
            <div class="stat-item" style="margin-left:auto;text-align:right"><div class="stat-lbl">% RSVP Yes</div><div class="stat-val" style="color:{RED}">{pct_yes}</div></div>
            <div class="stat-item" style="text-align:right"><div class="stat-lbl">% Pending</div><div class="stat-val" style="color:{GOLD}">{pct_pnd}</div></div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Resources
    st.markdown("---")
    st.markdown('<div class="gold-lbl">Resources</div>', unsafe_allow_html=True)
    rc1, rc2, rc3 = st.columns([2, 2, 4])
    with rc1:
        st.markdown('[📊 Event Guest List Template](https://docs.google.com/spreadsheets/d/1RneqrcCFo4X5tgZnBtHMF22nLpLZGuXLbzJKMmL7V8I/edit?gid=0#gid=0)', unsafe_allow_html=False)
    with rc2:
        st.markdown('[🔀 Guest List Overlap Checker](https://docs.google.com/spreadsheets/d/1iHnicmc4kKKWIzZlXgTfg1hCmjpbxHDvupT1s403rF4/edit?usp=drive_open&ouid=114687037818165116471)', unsafe_allow_html=False)


# ════════════════════════════════════════════════════════════════════════════
#  TAB 2 — EVENT DETAIL
# ════════════════════════════════════════════════════════════════════════════
with tab_detail:
    if not events:
        st.info("No events found.")
    else:
        event_names = [e["name"] for e in events]
        col_sel, col_splash = st.columns([4, 1])
        with col_sel:
            sel_name = st.selectbox("Select event:", event_names, key="detail_event")
        sel_event = next(e for e in events if e["name"] == sel_name)
        with col_splash:
            if sel_event["splash_url"]:
                st.markdown(f'<div style="padding-top:28px"><a href="{sel_event["splash_url"]}" target="_blank" style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;background:linear-gradient(135deg,{RED},#730011);color:white;border-radius:8px;font-size:12px;font-weight:700;text-decoration:none">↗ Go to Splash</a></div>', unsafe_allow_html=True)

        inv = sel_event["total_invited"]; yes = sel_event["total_confirmed"]
        no  = sel_event["total_declined"]; pnd = sel_event["total_pending"]
        att = sel_event["total_attended"]; nos = sel_event["total_no_shows"]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Invited",  f"{inv:,}")
        c2.metric("RSVP Yes", f"{yes:,}")
        c3.metric("RSVP No",  f"{no:,}")
        c4.metric("Pending",  f"{pnd:,}")
        c5,c6,c7,c8 = st.columns(4)
        c5.metric("Attended", f"{att:,}")
        c6.metric("No Show",  f"{nos:,}")
        c7.metric("% RSVP Yes", pct_str(yes, inv))
        c8.metric("% Pending",  pct_str(pnd, inv))

        col_ref, col_srch = st.columns([1, 1])
        with col_ref:
            if st.button("🔄 Refresh data", key="refresh_detail"):
                load_events.clear(); load_attendance.clear()
                st.rerun()

        st.markdown('<div class="gold-lbl" style="margin-top:12px">Guest list</div>', unsafe_allow_html=True)
        st.markdown('<div class="note-box">ℹ️ <strong>Event and Status</strong> is from the Airtable formula field <code>Event and Status</code> in Event Attendance. LinkedIn URL requires a People table join — available in this deployed app via the <code>load_people_linkedin()</code> lookup below.</div>', unsafe_allow_html=True)

        with st.spinner("Loading guests…"):
            guests = load_attendance(sel_event["id"])
            linkedin_lookup = load_people_linkedin()

        if not guests:
            st.info("No attendance records found.")
        else:
            df_guests = pd.DataFrame(guests)
            df_guests["LinkedIn"] = df_guests["Email"].str.lower().map(linkedin_lookup).fillna("")

            gcol1, gcol2, gcol3 = st.columns([2, 2, 4])
            with gcol1:
                rsvp_opts = ["All"] + sorted(df_guests["RSVP Status"].dropna().unique().tolist())
                sel_rsvp = st.selectbox("RSVP Status", rsvp_opts, key="det_rsvp")
            with gcol2:
                search = st.text_input("Search name / company", key="det_search", placeholder="Type to filter…")

            df_view = df_guests.copy()
            if sel_rsvp != "All":
                df_view = df_view[df_view["RSVP Status"] == sel_rsvp]
            if search:
                mask = (
                    df_view["Full Name"].str.contains(search, case=False, na=False) |
                    df_view["Company"].str.contains(search, case=False, na=False)
                )
                df_view = df_view[mask]

            st.caption(f"{len(df_view):,} records")

            # Display columns including LinkedIn and Event and Status
            display_cols = ["Full Name", "Email", "Title", "Company", "RSVP Status", "Seniority", "Event and Status", "LinkedIn"]
            st.dataframe(df_view[display_cols], use_container_width=True, hide_index=True,
                         height=min(600, len(df_view)*35+60))

            # Charts
            st.markdown('<div class="gold-lbl" style="margin-top:12px">Charts</div>', unsafe_allow_html=True)
            ch1, ch2 = st.columns(2)
            CHART_COLORS = [RED, SKY, GOLD, "#22c55e", "#a78bfa", "#f59e0b", "#ec4899", "#14b8a6"]

            with ch1:
                rsvp_counts = df_guests["RSVP Status"].value_counts().reset_index()
                rsvp_counts.columns = ["Status", "Count"]
                fig_r = px.pie(rsvp_counts, names="Status", values="Count", hole=0.55,
                               color_discrete_sequence=CHART_COLORS, title="RSVPs by status")
                fig_r.update_traces(textinfo="percent+label", textfont_size=11,
                                    textfont_color="white")
                fig_r.update_layout(showlegend=False, height=260, plot_bgcolor=BG,
                                    paper_bgcolor=BG, font_color="#DCE4C2",
                                    margin=dict(l=10,r=10,t=40,b=10),
                                    title_font_color=GOLD)
                st.plotly_chart(fig_r, use_container_width=True)

            with ch2:
                sen_counts = df_guests[df_guests["Seniority"].str.len() > 0]["Seniority"].value_counts().reset_index()
                sen_counts.columns = ["Seniority", "Count"]
                if not sen_counts.empty:
                    fig_s = px.pie(sen_counts, names="Seniority", values="Count", hole=0.55,
                                   color_discrete_sequence=CHART_COLORS, title="RSVPs by seniority")
                    fig_s.update_traces(textinfo="percent+label", textfont_size=11,
                                        textfont_color="white")
                    fig_s.update_layout(showlegend=False, height=260, plot_bgcolor=BG,
                                        paper_bgcolor=BG, font_color="#DCE4C2",
                                        margin=dict(l=10,r=10,t=40,b=10),
                                        title_font_color=GOLD)
                    st.plotly_chart(fig_s, use_container_width=True)

            # Company bar
            co_counts = df_guests[df_guests["Company"].str.len()>0]["Company"].value_counts().head(12).reset_index()
            co_counts.columns = ["Company", "Count"]
            if not co_counts.empty:
                fig_c = go.Figure(go.Bar(y=co_counts["Company"], x=co_counts["Count"],
                                         orientation="h", marker_color=RED, marker_cornerradius=3))
                fig_c.update_layout(
                    title="Top companies", title_font_color=GOLD,
                    height=max(200, len(co_counts)*36+80),
                    plot_bgcolor=BG, paper_bgcolor=BG, font_color="#DCE4C2",
                    xaxis=dict(gridcolor="#2a2626"),
                    yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10,r=10,t=40,b=10),
                )
                st.plotly_chart(fig_c, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
#  TAB 3 — PEOPLE
# ════════════════════════════════════════════════════════════════════════════
with tab_people:
    st.markdown('<div class="note-box">ℹ️ Showing all contacts from People table (1,103 total). <strong style="color:#DFB864">Engagement</strong> = Event Rollup from Event Attendance (events attended). LinkedIn URL from <code>LinkedIn URL (Source)</code> formula field.</div>', unsafe_allow_html=True)

    with st.spinner("Loading people…"):
        people_raw = airtable_get(
            PEOPLE_TABLE,
            params={"fields[]": ["Full Name", "Email", "Title", "Company",
                                  "Seniority (Source)", "LinkedIn URL (Source)",
                                  "Event Rollup (from Event Attendance)", "All Engagement"]}
        )

    people_rows = []
    for r in people_raw:
        f = r["fields"]
        name = (f.get("Full Name") or "").strip()
        if not name:
            continue
        ev_rollup = f.get("Event Rollup (from Event Attendance)")
        if isinstance(ev_rollup, list):
            engagement = ", ".join(str(x) for x in ev_rollup if x)
        elif ev_rollup:
            engagement = str(ev_rollup)
        else:
            engagement = ""

        people_rows.append({
            "Full Name":   name,
            "Email":       f.get("Email", ""),
            "Title":       f.get("Title", ""),
            "Company":     f.get("Company", ""),
            "Seniority":   f.get("Seniority (Source)", ""),
            "Engagement":  engagement,
            "LinkedIn":    f.get("LinkedIn URL (Source)", ""),
            "All Engagement": int(f.get("All Engagement")[0] if isinstance(f.get("All Engagement"), list) else (f.get("All Engagement") or 0)),
        })

    df_people = pd.DataFrame(people_rows)

    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("Total contacts", f"{len(df_people):,}")
    pc2.metric("With LinkedIn", f"{(df_people['LinkedIn'].str.len()>0).sum():,}")
    pc3.metric("Events tracked", 3)

    pf1, pf2, pf3 = st.columns([3, 2, 2])
    with pf1:
        p_search = st.text_input("Search name, company, title", key="p_search", placeholder="Type to filter…")
    with pf2:
        ev_opts = ["All events"] + ["Late Night", "BR Webinar", "Behind The Streams RSVP 2"]
        p_ev = st.selectbox("Event engagement", ev_opts, key="p_ev")
    with pf3:
        sen_opts = ["All seniority", "C-Suite", "VP / SVP / EVP", "Director", "Senior IC", "Manager", "IC", "Coordinator / Associate"]
        p_sen = st.selectbox("Seniority", sen_opts, key="p_sen")

    df_pview = df_people.copy()
    if p_search:
        mask = (
            df_pview["Full Name"].str.contains(p_search, case=False, na=False) |
            df_pview["Company"].str.contains(p_search, case=False, na=False) |
            df_pview["Title"].str.contains(p_search, case=False, na=False)
        )
        df_pview = df_pview[mask]
    if p_ev != "All events":
        df_pview = df_pview[df_pview["Engagement"].str.contains(p_ev, case=False, na=False)]
    if p_sen != "All seniority":
        df_pview = df_pview[df_pview["Seniority"] == p_sen]

    st.caption(f"{len(df_pview):,} contacts")
    st.dataframe(
        df_pview[["Full Name", "Email", "Title", "Company", "Engagement", "Seniority", "LinkedIn"]],
        use_container_width=True, hide_index=True,
        height=min(700, len(df_pview)*35+60),
    )


# ════════════════════════════════════════════════════════════════════════════
#  TAB 4 — CHANNEL HUB
# ════════════════════════════════════════════════════════════════════════════
with tab_channels:
    st.markdown('<div class="note-box">ℹ️ Channel Tracker has no Region or Countries columns. Region is derived from the Campaign ID prefix convention (e.g. [GLOBAL-], [UCAN-US]) which is a structured naming standard. Countries data is on the linked Project record.</div>', unsafe_allow_html=True)

    with st.spinner("Loading channels…"):
        channels = load_channels()

    df_ch = pd.DataFrame(channels)

    ch_f1, ch_f2, ch_f3, ch_f4 = st.columns(4)
    with ch_f1:
        type_opts = ["All types"] + sorted(df_ch["type"].dropna().unique().tolist())
        ch_type = st.selectbox("Channel type", type_opts, key="ch_type")
    with ch_f2:
        region_opts = ["All regions"] + sorted(df_ch["region"].dropna().unique().tolist())
        ch_region = st.selectbox("Region", region_opts, key="ch_region")
    with ch_f3:
        all_themes = sorted(set(t for themes in df_ch["themes"] for t in themes))
        theme_opts = ["All themes"] + all_themes
        ch_theme = st.selectbox("Content theme", theme_opts, key="ch_theme")

    # Apply filters
    df_filtered = df_ch.copy()
    if ch_type != "All types":
        df_filtered = df_filtered[df_filtered["type"] == ch_type]
    if ch_region != "All regions":
        df_filtered = df_filtered[df_filtered["region"] == ch_region]
    if ch_theme != "All themes":
        df_filtered = df_filtered[df_filtered["themes"].apply(lambda x: ch_theme in x)]

    c1,c2,c3 = st.columns(3)
    c1.metric("Future activations", df_filtered[df_filtered["is_future"]].shape[0])
    c2.metric("Channel types", df_filtered["type"].nunique())
    c3.metric("Total activations", len(df_filtered))

    # Roadmap
    st.markdown('<div class="gold-lbl" style="margin-top:8px">Channel roadmap — 2026</div>', unsafe_allow_html=True)

    CH_COLORS_BG = {"Organic Linkedin": ("rgba(143,194,230,.2)", SKY),
                    "Paid Linkedin":    ("rgba(139,92,246,.2)", "#a78bfa"),
                    "Email":            ("rgba(34,197,94,.2)", "#4ade80"),
                    "Amplification":    ("rgba(229,9,20,.15)", "#ff6b6b")}

    types_present = df_filtered["type"].dropna().unique()
    rm_html = '<div class="rm-wrap"><div class="rm-inner"><div class="rm-months"><div></div>'
    for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]:
        rm_html += f"<div>{m}</div>"
    rm_html += "</div>"

    for ch_t in types_present:
        bg, tc = CH_COLORS_BG.get(ch_t, ("rgba(107,114,128,.2)", "#9ca3af"))
        items = df_filtered[df_filtered["type"] == ch_t]
        rm_html += f'<div class="rm-row"><div class="rm-lbl">{ch_t}</div><div class="rm-track">'
        for mi in range(1, 13):
            cell = items[items["planned_date"].apply(
                lambda d: bool(d) and datetime.strptime(d, "%Y-%m-%d").month == mi if d else False
            )]
            rm_html += '<div class="rm-cell">'
            for _, row in cell.iterrows():
                rm_html += f'<span class="rm-pill" style="background:{bg};color:{tc}">{row["name"]}</span>'
            rm_html += "</div>"
        rm_html += "</div></div>"
    rm_html += "</div></div>"
    st.markdown(rm_html, unsafe_allow_html=True)

    # Future activations table — sorted by date, no status column
    st.markdown('<div class="gold-lbl">Future activations — sorted by planned date</div>', unsafe_allow_html=True)
    df_future = df_filtered[df_filtered["is_future"]].copy()
    df_future = df_future.sort_values("planned_date")
    df_future["Planned Date"] = df_future["planned_date"].apply(
        lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%b %-d, %Y") if d else "TBD"
    )
    df_future["Themes"] = df_future["themes"].apply(lambda x: ", ".join(x))
    df_future = df_future.rename(columns={"name": "Activation", "type": "Channel Type",
                                           "project": "Project", "region": "Region"})

    if df_future.empty:
        st.info("No future activations match current filters.")
    else:
        st.dataframe(
            df_future[["Activation", "Channel Type", "Planned Date", "Project", "Region", "Themes"]],
            use_container_width=True, hide_index=True,
        )
