"""ScholarPath - single-file AI scholarship agent. Run: uvicorn main:app"""
import os, json, time, uuid, anthropic
from datetime import date
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

DATA = r'''[
 {"name":"Chevening Scholarship","host":"UK","level":["masters"],"fields":["any"],"eligible":"countries_listed_on_site","min_work_years":2,"min_gpa_pct":60,"english":6.5,"funding":"full","typical_deadline_month":11,"url":"https://www.chevening.org"},
 {"name":"Fulbright Foreign Student Program","host":"USA","level":["masters","phd"],"fields":["any"],"eligible":"country_specific","min_work_years":0,"min_gpa_pct":65,"english":6.5,"funding":"full","typical_deadline_month":5,"url":"https://foreign.fulbrightonline.org"},
 {"name":"DAAD Development-Related Postgraduate Courses","host":"Germany","level":["masters"],"fields":["development","economics","public health","engineering","environment"],"eligible":"developing_countries","min_work_years":2,"min_gpa_pct":65,"english":6.0,"funding":"full","typical_deadline_month":10,"url":"https://www.daad.de"},
 {"name":"Erasmus Mundus Joint Masters","host":"Europe","level":["masters"],"fields":["any"],"eligible":"all","min_work_years":0,"min_gpa_pct":65,"english":6.5,"funding":"full","typical_deadline_month":1,"url":"https://erasmus-plus.ec.europa.eu"},
 {"name":"Gates Cambridge Scholarship","host":"UK","level":["masters","phd"],"fields":["any"],"eligible":"non_uk","min_work_years":0,"min_gpa_pct":80,"english":7.5,"funding":"full","typical_deadline_month":12,"url":"https://www.gatescambridge.org"},
 {"name":"Commonwealth Master's Scholarship","host":"UK","level":["masters"],"fields":["any"],"eligible":"commonwealth_lower_income","min_work_years":0,"min_gpa_pct":65,"english":6.5,"funding":"full","typical_deadline_month":10,"url":"https://cscuk.fcdo.gov.uk"},
 {"name":"Australia Awards Scholarships","host":"Australia","level":["masters","phd"],"fields":["any"],"eligible":"partner_countries","min_work_years":2,"min_gpa_pct":65,"english":6.5,"funding":"full","typical_deadline_month":4,"url":"https://www.dfat.gov.au/people-to-people/australia-awards"},
 {"name":"Swedish Institute Scholarships for Global Professionals","host":"Sweden","level":["masters"],"fields":["any"],"eligible":"listed_countries","min_work_years":3,"min_gpa_pct":65,"english":6.5,"funding":"full","typical_deadline_month":2,"url":"https://si.se/en/apply/scholarships"},
 {"name":"MEXT Japanese Government Scholarship","host":"Japan","level":["undergraduate","masters","phd"],"fields":["any"],"eligible":"country_specific","min_work_years":0,"min_gpa_pct":70,"english":0,"funding":"full","typical_deadline_month":5,"url":"https://www.studyinjapan.go.jp"},
 {"name":"Global Korea Scholarship (GKS)","host":"South Korea","level":["undergraduate","masters","phd"],"fields":["any"],"eligible":"country_specific","min_work_years":0,"min_gpa_pct":80,"english":0,"funding":"full","typical_deadline_month":2,"url":"https://www.studyinkorea.go.kr"},
 {"name":"Chinese Government Scholarship (CSC)","host":"China","level":["undergraduate","masters","phd"],"fields":["any"],"eligible":"all","min_work_years":0,"min_gpa_pct":70,"english":0,"funding":"full","typical_deadline_month":3,"url":"https://www.campuschina.org"},
 {"name":"Stipendium Hungaricum","host":"Hungary","level":["undergraduate","masters","phd"],"fields":["any"],"eligible":"partner_countries","min_work_years":0,"min_gpa_pct":60,"english":5.5,"funding":"full","typical_deadline_month":1,"url":"https://stipendiumhungaricum.hu"},
 {"name":"Turkiye Burslari","host":"Turkey","level":["undergraduate","masters","phd"],"fields":["any"],"eligible":"all","min_work_years":0,"min_gpa_pct":70,"english":0,"funding":"full","typical_deadline_month":2,"url":"https://turkiyeburslari.gov.tr"},
 {"name":"Knight-Hennessy Scholars (Stanford)","host":"USA","level":["masters","phd"],"fields":["any"],"eligible":"all","min_work_years":0,"min_gpa_pct":85,"english":7.0,"funding":"full","typical_deadline_month":10,"url":"https://knight-hennessy.stanford.edu"}
]
'''

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ScholarPath – find fully funded scholarships</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700&family=Public+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#f1f4f8;--panel:#fff;--ink:#14202e;--mute:#5b6b7c;--line:#d8e0e8;--acc:#1f4fd8;--accink:#fff;--me:#e6edff}
@media(prefers-color-scheme:dark){:root{--bg:#0f1722;--panel:#18222f;--ink:#e8eef5;--mute:#93a3b5;--line:#2a3747;--acc:#6f93ff;--accink:#0f1722;--me:#223257}}
*{box-sizing:border-box}html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 "Public Sans",system-ui,sans-serif;display:flex;justify-content:center}
main{width:100%;max-width:760px;display:flex;flex-direction:column;height:100%;padding:20px 16px}
h1{font:700 28px/1.15 "Bricolage Grotesque",system-ui;margin:0 0 4px}
p.sub{margin:0 0 14px;color:var(--mute)}
#log{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:12px;padding:4px 0}
.m{max-width:92%;padding:10px 14px;border-radius:12px;background:var(--panel);border:1px solid var(--line);overflow-wrap:anywhere}
.m.me{align-self:flex-end;background:var(--me);border-color:transparent}
.m a{color:var(--acc)}.m ul{padding-left:20px;margin:6px 0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.chips button{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:6px 12px;border-radius:999px;cursor:pointer;font:inherit;font-size:14px}
form{display:flex;gap:8px;padding-top:10px}
textarea{flex:1;resize:none;font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
button.send{background:var(--acc);color:var(--accink);border:0;border-radius:10px;padding:0 20px;font:500 16px "Public Sans";cursor:pointer}
button:focus-visible,textarea:focus-visible{outline:3px solid var(--acc);outline-offset:2px}
button:disabled{opacity:.5}
small{color:var(--mute);margin-top:8px}
</style></head><body><main>
<h1>ScholarPath</h1>
<p class="sub">Tell me your country, field, grades and English score. I rank fully funded scholarships and check current deadlines.</p>
<div class="chips" id="chips"></div>
<div id="log" aria-live="polite"></div>
<form id="f"><textarea id="t" rows="2" placeholder="e.g. Pakistani, BSc CS, 72%, 1 yr work, IELTS 6.5, want a Master's in AI" required></textarea><button class="send" id="b">Send</button></form>
<small>Always confirm details on the official scholarship site. Not a guarantee of admission or funding.</small>
</main><script>
const log=document.getElementById('log'),t=document.getElementById('t'),b=document.getElementById('b');
let sid=null;
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function md(s){s=esc(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
 s=s.replace(/(?:^|\n)((?:[-*] .+(?:\n|$))+)/g,(m,l)=>'<ul>'+l.trim().split('\n').map(x=>'<li>'+x.replace(/^[-*] /,'')+'</li>').join('')+'</ul>');
 return s.replace(/\n/g,'<br>').replace(/<\/ul><br>/g,'</ul>')}
function add(txt,me){const d=document.createElement('div');d.className='m'+(me?' me':'');d.innerHTML=me?esc(txt):md(txt);log.appendChild(d);log.scrollTop=log.scrollHeight;return d}
async function send(msg){add(msg,true);const w=add('Searching and checking sources…');b.disabled=true;
 try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sid,message:msg})});
  const j=await r.json();if(!r.ok)throw new Error(j.detail||'Request failed');sid=j.session_id;w.innerHTML=md(j.reply)}
 catch(e){w.textContent=e.message+' Check your connection and send again.'}
 b.disabled=false;log.scrollTop=log.scrollHeight}
f.onsubmit=e=>{e.preventDefault();const v=t.value.trim();if(!v)return;t.value='';send(v)};
t.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();f.requestSubmit()}};
['Fully funded Master\'s in Europe','PhD scholarships in engineering','Draft a statement of purpose','Make a 6-month application timeline'].forEach(x=>{const c=document.createElement('button');c.type='button';c.textContent=x;c.onclick=()=>{t.value=x;t.focus()};chips.appendChild(c)});
</script></body></html>
'''

# ---------------- matching algorithm ----------------
from datetime import date

DB = json.loads(DATA)

# Weights sum to 100
W = {"level": 20, "field": 20, "gpa": 20, "work": 15, "english": 15, "eligibility": 10}

def months_until(month: int, today: date | None = None) -> int:
    today = today or date.today()
    return (month - today.month) % 12

def score(profile: dict, s: dict) -> tuple[float, list[str], list[str]]:
    pros, cons, pts = [], [], 0.0
    level = profile.get("target_level", "masters").lower()
    if level not in s["level"]:
        return -1, [], [f"Does not fund {level}"]          # hard filter
    pts += W["level"]; pros.append(f"Funds {level}")

    field = profile.get("field", "").lower()
    if "any" in s["fields"]:
        pts += W["field"] * 0.8; pros.append("Open to all fields")
    elif any(f in field or field in f for f in s["fields"] if field):
        pts += W["field"]; pros.append("Field is a priority area")
    else:
        return -1, [], ["Field not covered"]               # hard filter

    gpa = float(profile.get("gpa_pct", 0) or 0)
    gap = gpa - s["min_gpa_pct"]
    if gap >= 0:
        pts += W["gpa"] * min(1.0, 0.6 + gap / 50); pros.append("Meets academic bar")
    else:
        pts += max(0, W["gpa"] * (1 + gap / 30)); cons.append(f"GPA {abs(gap):.0f} pts below typical minimum")

    yrs = float(profile.get("work_years", 0) or 0)
    if yrs >= s["min_work_years"]:
        pts += W["work"]
        if s["min_work_years"]: pros.append("Meets work-experience requirement")
    else:
        pts += W["work"] * yrs / max(1, s["min_work_years"])
        cons.append(f"Needs {s['min_work_years']}+ yrs work experience")

    ielts = float(profile.get("ielts", 0) or 0)
    if s["english"] == 0 or ielts >= s["english"]:
        pts += W["english"]
    else:
        pts += W["english"] * 0.4 if ielts else 0
        cons.append(f"IELTS {s['english']} typically required")

    nat = profile.get("nationality", "").lower()
    if s["eligible"] in ("all", "non_uk") and nat != "uk":
        pts += W["eligibility"]; pros.append("Broad nationality eligibility")
    else:
        pts += W["eligibility"] * 0.5
        cons.append("Nationality eligibility must be checked on official site")

    m = months_until(s["typical_deadline_month"])
    urgency = 5 if m <= 3 else 2 if m <= 6 else 0
    return min(100, pts + urgency), pros, cons

def match(profile: dict, top_k: int = 8) -> list[dict]:
    out = []
    for s in DB:
        sc, pros, cons = score(profile, s)
        if sc < 0: continue
        out.append({"name": s["name"], "host": s["host"], "score": round(sc, 1),
                    "funding": s["funding"], "typical_deadline_month": s["typical_deadline_month"],
                    "months_until_typical_deadline": months_until(s["typical_deadline_month"]),
                    "pros": pros, "cons": cons, "url": s["url"]})
    return sorted(out, key=lambda r: -r["score"])[:top_k]

# ---------------- agent loop ----------------

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
MAX_STEPS = 6

SYSTEM = """You are ScholarPath, an agent that helps students find fully funded scholarships for higher studies.
Workflow: (1) collect the profile (nationality, target level, field, GPA as %, work years, IELTS) - ask only for what is missing;
(2) call match_scholarships; (3) use web_search to verify the CURRENT deadline and eligibility for your top 3 picks before recommending them;
(4) give a ranked shortlist with why-it-fits, gaps to fix, and the next action with a date; (5) on request draft statements of purpose,
professor outreach emails, or a 6-month application timeline.
Rules: the built-in database holds typical deadlines only - never present them as current without verifying. Always link the official site.
Never invent scholarships. Never guarantee outcomes. Be concise."""

TOOLS = [
    {"name": "match_scholarships",
     "description": "Rank scholarships in the built-in database against the student's profile.",
     "input_schema": {"type": "object", "properties": {
         "nationality": {"type": "string"},
         "target_level": {"type": "string", "enum": ["undergraduate", "masters", "phd"]},
         "field": {"type": "string"},
         "gpa_pct": {"type": "number", "description": "GPA converted to a percentage"},
         "work_years": {"type": "number"},
         "ielts": {"type": "number"}},
         "required": ["target_level"]}},
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
]

def run_tool(name: str, args: dict) -> str:
    if name == "match_scholarships":
        return json.dumps(match(args))
    return "unknown tool"

def chat(history: list[dict]) -> str:
    for _ in range(MAX_STEPS):
        resp = client.messages.create(model=MODEL, max_tokens=2000, system=SYSTEM,
                                      tools=TOOLS, messages=history)
        history.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "pause_turn":          # long server-side search: resume
            continue
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        results = [{"type": "tool_result", "tool_use_id": b.id, "content": run_tool(b.name, b.input)}
                   for b in resp.content if b.type == "tool_use"]
        history.append({"role": "user", "content": results})
    return "I hit my step limit - please narrow the question and try again."

# ---------------- web server ----------------
app = FastAPI(title="ScholarPath")
SESSIONS: dict[str, list] = {}
HITS: dict[str, deque] = defaultdict(deque)
LIMIT, WINDOW = 15, 3600  # 15 requests / hour / IP (protects your API bill)

class Msg(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=3000)

@app.post("/api/chat")
def api_chat(body: Msg, request: Request):
    ip = request.client.host if request.client else "x"
    q, now = HITS[ip], time.time()
    while q and now - q[0] > WINDOW: q.popleft()
    if len(q) >= LIMIT: raise HTTPException(429, "Hourly limit reached. Try again later.")
    q.append(now)
    sid = body.session_id or uuid.uuid4().hex
    hist = SESSIONS.setdefault(sid, [])
    hist.append({"role": "user", "content": body.message})
    try:
        reply = chat(hist)
    except Exception:
        hist.pop(); raise HTTPException(502, "The agent failed. Please retry.")
    if len(hist) > 40: del hist[:-40]
    return {"session_id": sid, "reply": reply}

@app.get("/health")
def health(): return {"ok": True}

@app.get("/")
def home(): return HTMLResponse(HTML)
