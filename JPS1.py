import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import json

# ============================================================
# 【データ層】 史実マスター / イベント定義
# ============================================================

EVENTS = {
    1947: {"name": "日本国憲法 施行", "desc": "平和主義・民主主義が定着し始めました。"},
    1950: {"name": "朝鮮特需", "desc": "隣国での戦争により、日本の製造業に大量の発注が舞い込みました。"},
    1964: {"name": "東京オリンピック", "desc": "インフラ整備が進み、国際社会への復帰を強く印象付けました。"},
    1973: {"name": "第一次オイルショック", "desc": "原油価格が急騰。インフレが進行しています。"},
    1985: {"name": "プラザ合意", "desc": "急激な円高が進行し、輸出産業が打撃を受けています。"},
    1991: {"name": "バブル崩壊", "desc": "資産価格が急落し、不良債権問題が顕在化しました。"},
    2008: {"name": "リーマン・ショック", "desc": "世界的な金融危機で輸出を中心に大きな打撃を受けました。"},
    2011: {"name": "東日本大震災", "desc": "未曾有の大震災と原発事故が発生。サプライチェーンが寸断されました。"},
    2020: {"name": "COVID-19 パンデミック", "desc": "新型感染症の世界的流行により、経済活動が大きく制限されています。"},
}

def generate_hist_data():
    data = {}
    for y in range(1945, 2026):
        p = min(1.0, (y - 1945) / 45.0)
        g = int(0 + 200 * p if y <= 1990 else 200 + 20 * (y - 1990) / 35.0)
        w = int(2 + 100 * p)
        m = int(2 + 40 * p)
        d = int(30 + 70 * p)
        t = int(0 + 150 * p)
        np_v = int(g * 0.25 + w * 0.15 + m * 0.25 + d * 0.15 + t * 0.20)
        data[y] = {'gdp': g, 'welfare': w, 'military': m, 'diplomacy': d, 'tech': t, 'np': np_v}
    return data

HIST = generate_hist_data()
SCALE = 2.0
W = {'gdp': .25, 'welfare': .15, 'military': .25, 'diplomacy': .15, 'tech': .20}

# ============================================================
# 【エンジン層】 指標計算
# ============================================================

def calc_hi(d):
    return {
        'gdp':      round(100 + (d['econCap'] * 0.50 + d['humanCap'] * 0.25 + d['researchCap'] * 0.15) * SCALE),
        'welfare':  round(100 + (d['socialDev'] * 0.45 + d['humanCap'] * 0.25 + d['econCap'] * 0.10) * SCALE),
        'military': round(100 + d['milCap'] * SCALE),
        'diplomacy':round(100 + (d['diplomNet'] * 0.70 + d['econCap'] * 0.10) * SCALE),
        'tech':     round(100 + (d['researchCap'] * 0.50 + d['humanCap'] * 0.35 + d['econCap'] * 0.15) * SCALE),
    }

def calc_np(hi, yr):
    h = HIST[yr]
    gNP = (h['gdp'] * (hi['gdp'] / 100) * W['gdp'] +
           h['welfare'] * (hi['welfare'] / 100) * W['welfare'] +
           h['military'] * (hi['military'] / 100) * W['military'] +
           h['diplomacy'] * (hi['diplomacy'] / 100) * W['diplomacy'] +
           h['tech'] * (hi['tech'] / 100) * W['tech'])
    return round(gNP / max(1, h['np']) * 100)

# ============================================================
# 【AIレイヤー】 Gemini 呼び出し
# ============================================================

def call_ai(prompt, as_json=True):
    if "GEMINI_API_KEY" not in st.secrets:
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-2.0-flash')
        resp = model.generate_content(prompt).text
        if as_json:
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp:   resp = resp.split("```")[1].split("```")[0]
            return json.loads(resp.strip())
        return resp
    except Exception as e:
        st.error(f"AI処理エラー: {e}")
        return None

# ============================================================
# 【UI設計】 定数・ヘルパー関数
# ============================================================

ERA_CONFIG = [
    (1945, 1952, "占領期",         "🔴", "#8B3A3A", "#2A0808", "GHQ占領下 — 廃墟からの出発"),
    (1953, 1960, "復興・高度成長期","🟡", "#B8902A", "#281808", "朝鮮特需〜所得倍増計画の夜明け"),
    (1961, 1973, "高度経済成長期",  "🟢", "#2A8B5A", "#081808", "奇跡の成長 — GDPが世界第2位へ"),
    (1974, 1990, "安定成長・バブル","🔵", "#2A5A8B", "#081828", "石油危機克服〜バブル景気"),
    (1991, 2025, "現代",           "⚪", "#6A7A8B", "#101618", "バブル崩壊から令和へ"),
]

def get_era(yr):
    for s, e, name, icon, col, bg, desc in ERA_CONFIG:
        if s <= yr <= e:
            return {"name": name, "icon": icon, "color": col, "bar_bg": bg, "desc": desc}
    return {"name": "現代", "icon": "⚪", "color": "#6A7A8B", "bar_bg": "#101618", "desc": ""}

def hi_color(v):
    if v >= 115: return "#3AB888"
    if v >= 103: return "#7EC4B0"
    if v <= 85:  return "#C85050"
    if v <= 97:  return "#C09090"
    return "#C8D8EC"

def bar_color(v):
    if v >= 110: return "#3AB888"
    if v >= 100: return "#7EC4B0"
    if v >=  90: return "#D4A83C"
    return "#C85050"

def get_approval(hi, state):
    wf  = hi.get('welfare', 100) - 100
    gd  = (hi.get('gdp', 100) - 100) * 0.5
    inf_pen  = max(0, state.get('inflation', 5) - 5)  * -3
    debt_pen = max(0, state.get('debt', 50) - 80)     * -1
    return int(max(10, min(95, 50 + wf * 0.3 + gd * 0.2 + inf_pen + debt_pen)))

# ─── HTML コンポーネント ─────────────────────────────────────

def c_indicator(name, icon, val, note=""):
    col  = hi_color(val)
    bcol = bar_color(val)
    pct  = min(100, val / 1.5)
    delta = val - 100
    sign = "▲" if delta >= 0 else "▼"
    dc   = "#3AB888" if delta >= 0 else "#C85050"
    extra = f" — {note}" if note else ""
    return f"""
<div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;
            padding:9px 11px;margin-bottom:6px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
    <span style="font-size:11px;color:#607890">{icon} {name}</span>
    <span style="font-size:17px;font-weight:700;color:{col}">{val}</span>
  </div>
  <div style="height:3px;background:#1C2A4A;border-radius:2px;overflow:hidden;margin-bottom:4px">
    <div style="height:100%;width:{pct}%;background:{bcol};border-radius:2px"></div>
  </div>
  <div style="font-size:9px;color:{dc}">{sign}{abs(delta)}% vs 史実{extra}</div>
</div>"""

def c_minister(name, icon, cls, text):
    styles = {
        'fin': ("#0A1828", "#1C3A6A", "#4888D4"),
        'eco': ("#1A1208", "#4A3A10", "#D4A83C"),
        'wel': ("#081818", "#1A4A28", "#3AB888"),
        'opp': ("#180808", "#4A1A1A", "#C85050"),
    }
    bg, bd, nc = styles.get(cls, styles['fin'])
    return f"""
<div style="background:{bg};border:1px solid {bd};border-radius:9px;
            padding:11px 13px;margin-bottom:8px">
  <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px">
    <span style="font-size:18px">{icon}</span>
    <span style="font-size:11px;font-weight:600;color:{nc}">{name}</span>
  </div>
  <div style="font-size:12px;color:#607890;line-height:1.65">{text}</div>
</div>"""

def c_citizen(name, icon, detail, text):
    return f"""
<div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;
            padding:11px 13px;margin-bottom:7px">
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
    <span style="font-size:20px">{icon}</span>
    <div>
      <div style="font-size:12px;font-weight:600;color:#C8D8EC">{name}</div>
      <div style="font-size:9px;color:#2E4060">{detail}</div>
    </div>
  </div>
  <div style="font-size:12px;color:#607890;line-height:1.65">{text}</div>
</div>"""

def c_japan_map(welfare_val):
    rc = bar_color(welfare_val)
    gc = bar_color(max(60, welfare_val - 10))
    return f"""
<div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;
            padding:10px;text-align:center">
  <div style="font-size:9px;color:#2E4060;letter-spacing:.1em;margin-bottom:8px">地域別満足度マップ</div>
  <svg viewBox="0 0 180 320" width="130" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="140" cy="30" rx="32" ry="22" fill="{rc}" opacity=".7"/>
    <text x="140" y="35" text-anchor="middle" font-size="8" fill="#C8D8EC">北海道</text>
    <path d="M110 55 Q120 50 130 60 L125 90 Q115 100 105 95 Q100 80 110 55Z" fill="{rc}" opacity=".7"/>
    <text x="116" y="78" text-anchor="middle" font-size="7" fill="#C8D8EC">東北</text>
    <path d="M95 100 Q115 95 125 105 L120 130 Q110 140 95 135 Q85 125 95 100Z" fill="{rc}" opacity=".85"/>
    <text x="107" y="118" text-anchor="middle" font-size="7" fill="#C8D8EC">関東★</text>
    <path d="M78 135 Q100 130 110 145 L100 168 Q88 175 76 165 Q70 152 78 135Z" fill="{rc}" opacity=".7"/>
    <text x="93" y="155" text-anchor="middle" font-size="7" fill="#C8D8EC">中部</text>
    <path d="M62 168 Q80 162 88 175 L82 198 Q72 205 60 198 Q54 185 62 168Z" fill="{rc}" opacity=".7"/>
    <text x="73" y="186" text-anchor="middle" font-size="7" fill="#C8D8EC">近畿</text>
    <path d="M45 200 Q70 196 78 210 L70 230 Q58 235 46 228 Q40 216 45 200Z" fill="{gc}" opacity=".65"/>
    <text x="60" y="218" text-anchor="middle" font-size="7" fill="#C8D8EC">中四国</text>
    <path d="M30 235 Q55 230 60 248 L50 278 Q38 285 26 275 Q20 258 30 235Z" fill="{rc}" opacity=".7"/>
    <text x="42" y="260" text-anchor="middle" font-size="7" fill="#C8D8EC">九州</text>
    <ellipse cx="35" cy="302" rx="12" ry="8" fill="{rc}" opacity=".6"/>
    <text x="35" y="306" text-anchor="middle" font-size="6" fill="#C8D8EC">沖縄</text>
  </svg>
  <div style="display:flex;gap:8px;justify-content:center;margin-top:6px">
    <span style="font-size:9px;color:#3AB888">● 高</span>
    <span style="font-size:9px;color:#D4A83C">● 普通</span>
    <span style="font-size:9px;color:#C85050">● 低</span>
  </div>
</div>"""

def c_section(label):
    return f'<div style="font-size:9px;color:#2E4060;letter-spacing:.12em;padding-bottom:6px;border-bottom:1px solid #141E38;margin-bottom:8px">{label}</div>'

# ─── CSS ─────────────────────────────────────────────────────

DARK_CSS = """
<style>
.stApp,[data-testid="stAppViewContainer"]{background-color:#04060C!important;color:#C8D8EC!important;}
[data-testid="stHeader"]{background-color:#04060C!important;}
[data-testid="stSidebar"]{background-color:#04060C!important;}
.stTabs [data-baseweb="tab-list"]{background:#08101C;border-radius:0;border-bottom:1px solid #1C2A4A;gap:2px;padding:0 12px;}
.stTabs [data-baseweb="tab"]{color:#607890!important;background:transparent!important;
  border-bottom:2px solid transparent!important;border-radius:0!important;
  padding:9px 16px!important;font-size:13px!important;font-weight:600!important;}
.stTabs [aria-selected="true"]{color:#D4A83C!important;border-bottom:2px solid #D4A83C!important;}
.stButton>button{background-color:#D4A83C!important;color:#04060C!important;
  font-weight:700!important;border:none!important;border-radius:7px!important;padding:10px 20px!important;}
.stButton>button:hover{background-color:#F0C050!important;}
.stTextArea>div>textarea{background-color:#0D1828!important;color:#C8D8EC!important;
  border:1px solid #253858!important;border-radius:7px!important;}
.stTextArea>div>textarea:focus{border-color:#4888D4!important;box-shadow:none!important;}
.stTextArea label,.stMarkdown p,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3{color:#C8D8EC!important;}
[data-testid="stMetricValue"]{color:#C8D8EC!important;}
[data-testid="stMetricLabel"]{color:#607890!important;}
div[data-testid="stAlert"]{background:#1A1000;border:1px solid #D48030;border-radius:9px;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:#253858;border-radius:2px;}
</style>"""

# ============================================================
# 【メインアプリ】
# ============================================================

st.set_page_config(
    page_title="🇯🇵 日本国家シミュレーション",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🇯🇵"
)
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ─── セッション初期化 ─────────────────────────────────────────

if 'year' not in st.session_state:
    st.session_state.year     = 1945
    st.session_state.state    = {
        'econCap':0,'humanCap':0,'socialDev':0,'milCap':0,'diplomNet':0,'researchCap':0,
        'inflation':8.0,'debt':15.0
    }
    st.session_state.history  = []
    st.session_state.ai_news  = {}
    st.session_state.ai_proposal = None
    st.session_state.event_msg   = ""

# ─── 現在値計算 ───────────────────────────────────────────────

yr       = st.session_state.year
state    = st.session_state.state
hi       = calc_hi(state)
np_val   = calc_np(hi, yr)
approval = get_approval(hi, state)
era      = get_era(yr)

# ─── ヘッダー ─────────────────────────────────────────────────

ap_col = "#3AB888" if approval >= 60 else "#D4A83C" if approval >= 35 else "#C85050"
np_col = hi_color(np_val)
np_sign = "▲" if np_val >= 100 else "▼"
inf_col = "#3AB888" if state['inflation'] < 5 else "#D4A83C" if state['inflation'] < 8 else "#C85050"
dbt_col = "#D4A83C" if state['debt'] < 80 else "#C85050"

st.markdown(f"""
<style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}</style>
<div style="background:{era['bar_bg']};border-bottom:1px solid {era['color']}44;
            padding:5px 20px;display:flex;align-items:center;gap:10px;
            font-size:10px;color:{era['color']};letter-spacing:.08em">
  <span style="width:6px;height:6px;border-radius:50%;background:{era['color']};
               display:inline-block;animation:pulse 2s infinite"></span>
  {era['icon']} {era['name']} — {era['desc']}
  <span style="margin-left:auto;color:#2E4060">ターン {yr - 1945 + 1} / 81</span>
</div>
<div style="background:#08101C;border-bottom:1px solid #1C2A4A;padding:10px 20px;
            display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
  <div style="display:flex;align-items:baseline;gap:10px">
    <span style="font-size:28px">🇯🇵</span>
    <div>
      <div style="font-size:34px;font-weight:700;color:#D4A83C;line-height:1">{yr}年</div>
      <div style="font-size:10px;color:#2E4060">昭和{yr-1925}年</div>
    </div>
  </div>
  <div style="display:flex;gap:10px;flex-wrap:wrap">
    <div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;padding:8px 14px;text-align:center;min-width:90px">
      <div style="font-size:22px;font-weight:700;color:{np_col}">{np_val}</div>
      <div style="font-size:9px;color:#2E4060;letter-spacing:.04em">総合国力HI</div>
      <div style="font-size:10px;color:{np_col}">{np_sign}{abs(np_val-100)}% vs史実</div>
    </div>
    <div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;padding:8px 14px;text-align:center;min-width:90px">
      <div style="font-size:22px;font-weight:700;color:{inf_col}">{state['inflation']:.1f}%</div>
      <div style="font-size:9px;color:#2E4060;letter-spacing:.04em">インフレ率</div>
      <div style="font-size:10px;color:{'#3AB888' if state['inflation']<5 else '#D4A83C'}">{"適正" if state['inflation']<5 else "注意" if state['inflation']<8 else "危険"}</div>
    </div>
    <div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;padding:8px 14px;text-align:center;min-width:90px">
      <div style="font-size:22px;font-weight:700;color:{dbt_col}">{state['debt']:.1f}%</div>
      <div style="font-size:9px;color:#2E4060;letter-spacing:.04em">債務/GDP比</div>
      <div style="font-size:10px;color:{dbt_col}">{"安全" if state['debt']<60 else "注意" if state['debt']<80 else "危険"}</div>
    </div>
  </div>
  <div style="text-align:center;min-width:120px">
    <div style="font-size:28px;font-weight:700;color:{ap_col}">{approval}%</div>
    <div style="font-size:9px;color:#2E4060;letter-spacing:.04em;margin-bottom:5px">政府支持率</div>
    <div style="height:8px;width:120px;background:#1C2A4A;border-radius:4px;overflow:hidden">
      <div style="height:100%;width:{approval}%;background:{ap_col};border-radius:4px"></div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

if yr >= 2026:
    st.success("🏁 2025年を突破！ここからはAIによる未来シミュレーションです。")

# ─── タブ ─────────────────────────────────────────────────────

tab_pol, tab_news, tab_data = st.tabs(["🏛️ 政策・AI閣議", "📰 ニュース・国民の声", "📊 国家データ"])

# ═══ TAB: 政策・AI閣議 ═══════════════════════════════════════

with tab_pol:

    # 歴史イベントアラート
    if st.session_state.event_msg:
        st.markdown(f"""
<div style="background:#1A1000;border:1px solid #D48030;border-radius:9px;padding:12px 15px;margin-bottom:14px">
  <div style="font-size:10px;font-weight:700;color:#D48030;letter-spacing:.06em;margin-bottom:5px">🔔 歴史イベント発生</div>
  <div style="font-size:13px;color:#C8D8EC">{st.session_state.event_msg}</div>
</div>""", unsafe_allow_html=True)

    col_dash, col_cab = st.columns([2, 3], gap="medium")

    # ── 左列: ダッシュボード ────────────────────────────────────
    with col_dash:

        # 総合国力ヒーロー
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#121F34,#0D1828);border:1px solid #253858;
            border-radius:10px;padding:16px;text-align:center;margin-bottom:12px">
  <div style="font-size:52px;font-weight:700;color:#D4A83C;line-height:1">{np_val}</div>
  <div style="font-size:10px;color:#2E4060;letter-spacing:.1em;margin-top:4px">総合国力 Historical Index</div>
  <div style="font-size:12px;color:{np_col};margin-top:6px">
    {'▲' if np_val>=100 else '▼'}{abs(np_val-100)}% — 史実の日本を{'上回っています' if np_val>=100 else '下回っています'}
  </div>
</div>""", unsafe_allow_html=True)

        # 5指標
        st.markdown(c_section("📊 指標 — HISTORICAL INDEX"), unsafe_allow_html=True)
        for name, icon, key, note in [
            ("GDP",    "💴", "gdp",      ""),
            ("国民福祉","🏥","welfare",   ""),
            ("軍事力", "⚔️","military",  f"上限{min(20, int(state['milCap'])+20)}"),
            ("外交力", "🤝","diplomacy", ""),
            ("技術力", "⚙️","tech",      ""),
        ]:
            st.markdown(c_indicator(name, icon, hi[key], note), unsafe_allow_html=True)

        # マクロ経済
        st.markdown(c_section("💹 マクロ経済"), unsafe_allow_html=True)
        mc1, mc2 = st.columns(2)
        with mc1:
            ic = "#3AB888" if state['inflation']<5 else "#D4A83C" if state['inflation']<8 else "#C85050"
            st.markdown(f"""
<div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;padding:9px;text-align:center">
  <div style="font-size:20px;font-weight:700;color:{ic}">{state['inflation']:.1f}%</div>
  <div style="font-size:9px;color:#2E4060;margin-top:2px">インフレ率</div>
  <div style="font-size:9px;color:{ic}">{"✓ 適正" if state['inflation']<5 else "⚠ 注意" if state['inflation']<8 else "🔴 危険"}</div>
</div>""", unsafe_allow_html=True)
        with mc2:
            dc = "#D4A83C" if state['debt']<80 else "#C85050"
            st.markdown(f"""
<div style="background:#0D1828;border:1px solid #1C2A4A;border-radius:8px;padding:9px;text-align:center">
  <div style="font-size:20px;font-weight:700;color:{dc}">{state['debt']:.1f}%</div>
  <div style="font-size:9px;color:#2E4060;margin-top:2px">債務/GDP比</div>
  <div style="font-size:9px;color:{dc}">{"✓ 安全" if state['debt']<60 else "⚠ 注意" if state['debt']<80 else "🔴 危険"}</div>
</div>""", unsafe_allow_html=True)

        # 日本地図
        st.markdown(c_section("🗾 地域別満足度"), unsafe_allow_html=True)
        st.markdown(c_japan_map(hi['welfare']), unsafe_allow_html=True)

    # ── 右列: AI閣議 ────────────────────────────────────────────
    with col_cab:

        st.markdown(c_section("🎙️ AI閣議室 — 首相への提言"), unsafe_allow_html=True)

        directive = st.text_area(
            "label", height=82, label_visibility="collapsed",
            placeholder="首相として今期の方針を入力してください\n例：インフレを抑えつつ教育投資を強化し、農村と都市の格差を解消したい。"
        )
        st.markdown('<div style="font-size:10px;color:#2E4060;margin:-6px 0 8px">💡 自然言語で入力するとAIが政策案と閣僚の見解を生成します</div>', unsafe_allow_html=True)

        if st.button("🏛️ 補佐官に政策案を作成させる", use_container_width=True):
            if directive.strip():
                with st.spinner("AIが現状データを分析し、政策パッケージと閣僚の意見を生成中..."):
                    prompt = f"""あなたは{yr}年の日本のAI首相補佐官です。
現在: GDP指数{hi['gdp']}, 福祉{hi['welfare']}, インフレ{state['inflation']:.1f}%, 債務{state['debt']:.1f}%
時代: {era['name']} — {era['desc']}
首相の指示:「{directive}」

以下のJSONで回答してください（時代考証を厳守）:
{{
  "proposal_name": "政策パッケージ名（20文字以内）",
  "analysis": "現状分析と効果の解説（80〜100文字）",
  "cabinet": {{
    "財務大臣": "財政的視点（40〜60文字）",
    "経産大臣": "産業・成長視点（40〜60文字）",
    "厚労大臣": "国民生活視点（40〜60文字）",
    "野党党首": "批判的意見（40〜60文字）"
  }},
  "effects": {{
    "econCap": 0, "humanCap": 0, "socialDev": 0,
    "milCap": 0, "diplomNet": 0, "researchCap": 0,
    "inflation_change": 0.0, "debt_change": 0.0
  }}
}}"""
                    resp = call_ai(prompt, as_json=True)
                    if resp:
                        st.session_state.ai_proposal = resp
                        st.rerun()
            else:
                st.warning("⚠️ 方針を入力してください")

        if st.session_state.ai_proposal:
            prop = st.session_state.ai_proposal
            eff  = prop.get('effects', {})

            # 政策提案カード
            tags_html = ""
            labels = {'econCap':'経済','humanCap':'人材','socialDev':'社会',
                      'milCap':'軍事','diplomNet':'外交','researchCap':'技術'}
            for k, lbl in labels.items():
                v = eff.get(k, 0)
                if v != 0:
                    pos = v > 0
                    bg  = "rgba(58,184,136,.15)" if pos else "rgba(200,80,80,.15)"
                    bc  = "rgba(58,184,136,.3)"  if pos else "rgba(200,80,80,.3)"
                    col = "#3AB888" if pos else "#C85050"
                    tags_html += f'<span style="background:{bg};color:{col};border:1px solid {bc};border-radius:4px;font-size:10px;padding:2px 7px;font-weight:600;margin:2px">{lbl} {"+" if pos else ""}{v}</span>'
            if eff.get('inflation_change', 0) != 0:
                v = eff['inflation_change']; pos = v < 0
                bg  = "rgba(58,184,136,.15)" if pos else "rgba(200,80,80,.15)"
                bc  = "rgba(58,184,136,.3)"  if pos else "rgba(200,80,80,.3)"
                col = "#3AB888" if pos else "#C85050"
                tags_html += f'<span style="background:{bg};color:{col};border:1px solid {bc};border-radius:4px;font-size:10px;padding:2px 7px;font-weight:600;margin:2px">インフレ {"+" if v>0 else ""}{v:.1f}%</span>'

            st.markdown(f"""
<div style="background:linear-gradient(135deg,#0A1E10,#121F34);border:1px solid #1A4A28;
            border-radius:10px;padding:14px;margin:10px 0">
  <div style="font-size:14px;font-weight:700;color:#4AE890;margin-bottom:7px">
    📋 {prop.get('proposal_name','政策案')}
  </div>
  <div style="font-size:12px;color:#607890;line-height:1.75;margin-bottom:10px">
    {prop.get('analysis','')}
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:4px">{tags_html}</div>
</div>""", unsafe_allow_html=True)

            # 閣僚カード
            st.markdown(c_section("🏛️ 閣僚の見解"), unsafe_allow_html=True)
            cab = prop.get('cabinet', {})
            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown(c_minister("財務大臣","💰","fin", cab.get("財務大臣","")), unsafe_allow_html=True)
                st.markdown(c_minister("厚労大臣","🏥","wel", cab.get("厚労大臣","")), unsafe_allow_html=True)
            with mc2:
                st.markdown(c_minister("経産大臣","🏭","eco", cab.get("経産大臣","")), unsafe_allow_html=True)
                st.markdown(c_minister("野党党首","🔴","opp", cab.get("野党党首","")), unsafe_allow_html=True)

            if st.button(f"✅ この政策を実行して {yr+1}年 へ進む", use_container_width=True):
                # パラメータ更新
                for k in ['econCap','humanCap','socialDev','milCap','diplomNet','researchCap']:
                    state[k] += eff.get(k, 0)
                state['inflation'] = max(0, state['inflation'] + eff.get('inflation_change', 0.0))
                state['debt']     += eff.get('debt_change', 0.0)

                # 履歴保存
                st.session_state.history.append({
                    'year': yr, 'np': np_val, 'gdp': hi['gdp'], 'welfare': hi['welfare'],
                    'inflation': state['inflation'], 'debt': state['debt'],
                    'approval': approval, 'policy': prop.get('proposal_name','')
                })

                # ニュース・国民生成
                with st.spinner("AIがニュースと国民の声を生成中..."):
                    np2 = f"""
{yr}年日本。政策「{prop.get('proposal_name','')}」を実行。
インフレ{state['inflation']:.1f}%、GDP指数{hi['gdp']}、時代:{era['name']}
以下JSONで時代考証を反映したリアルな反応を生成してください:
{{
  "news_headline": "【AI日経速報】見出し（25〜35文字）",
  "news_body": "記事本文（100〜130文字、2〜3段落）",
  "worker":  "製造業労働者30代の本音（40〜60文字）",
  "farmer":  "地方農家50代の本音（40〜60文字）",
  "student": "大学生20代の本音（40〜60文字）",
  "elder":   "高齢者70代の本音（40〜60文字）"
}}"""
                    nr = call_ai(np2, as_json=True)
                    if nr: st.session_state.ai_news = nr

                # ターン進行
                st.session_state.year        += 1
                st.session_state.ai_proposal  = None
                ev = EVENTS.get(st.session_state.year)
                st.session_state.event_msg = f"【{ev['name']}】 {ev['desc']}" if ev else ""
                st.rerun()

# ═══ TAB: ニュース・国民の声 ═══════════════════════════════════

with tab_news:
    news = st.session_state.ai_news
    if news:
        nc1, nc2 = st.columns([3, 2], gap="medium")
        with nc1:
            body_html = news.get('news_body','').replace('\n','<br>')
            st.markdown(f"""
<div style="background:#0D1828;border:1px solid #253858;border-radius:10px;padding:22px">
  <div style="text-align:center;border-bottom:2px solid #607890;padding-bottom:12px;margin-bottom:16px">
    <div style="font-size:20px;font-weight:700;color:#C8D8EC;letter-spacing:.05em">AI日本経済新聞</div>
    <div style="font-size:10px;color:#2E4060;margin-top:3px;letter-spacing:.1em">
      {yr-1}年（昭和{yr-1-1925}年） ／ ゲーム内仮想紙面
    </div>
  </div>
  <div style="font-size:19px;font-weight:700;color:#C8D8EC;margin-bottom:8px;line-height:1.4">
    {news.get('news_headline','')}
  </div>
  <div style="font-size:12px;color:#607890;line-height:1.85">{body_html}</div>
</div>""", unsafe_allow_html=True)

        with nc2:
            st.markdown(c_section("🗣️ 国民の声"), unsafe_allow_html=True)
            citizens = [
                ("製造業労働者","👷","30代・東海地方","worker"),
                ("地方農家",   "🌾","50代・東北地方","farmer"),
                ("大学生",     "🎓","20代・東京",    "student"),
                ("高齢者",     "👴","70代・九州",     "elder"),
            ]
            for name, icon, detail, key in citizens:
                t = news.get(key,'')
                if t:
                    st.markdown(c_citizen(name, icon, detail, t), unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="text-align:center;padding:80px 20px;color:#2E4060">
  <div style="font-size:52px;margin-bottom:16px">📰</div>
  <div style="font-size:16px;margin-bottom:8px">まだニュースはありません</div>
  <div style="font-size:12px">政策を実行するとAIがニュースと国民の声を生成します</div>
</div>""", unsafe_allow_html=True)

# ═══ TAB: 国家データ ═══════════════════════════════════════════

with tab_data:
    hist = st.session_state.history
    if hist:
        df = pd.DataFrame(hist)
        PLOT_LAYOUT = dict(
            paper_bgcolor='#0D1828', plot_bgcolor='#0D1828',
            font=dict(color='#607890', size=11),
            title_font=dict(color='#C8D8EC', size=13),
            legend=dict(bgcolor='#0D1828', bordercolor='#1C2A4A', borderwidth=1),
            xaxis=dict(gridcolor='#1C2A4A', linecolor='#1C2A4A', title_font_color='#607890'),
            yaxis=dict(gridcolor='#1C2A4A', linecolor='#1C2A4A', title_font_color='#607890'),
            margin=dict(l=10, r=10, t=45, b=10)
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            fig1 = px.line(df, x="year", y=["np","gdp","welfare"], markers=True,
                           color_discrete_map={"np":"#D4A83C","gdp":"#4888D4","welfare":"#3AB888"},
                           labels={"value":"指数","variable":"指標","year":"年"},
                           title="国家成長軌跡 (総合国力・GDP・福祉)")
            fig1.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig1, use_container_width=True)
        with dc2:
            fig2 = px.line(df, x="year", y=["inflation","debt"], markers=True,
                           color_discrete_map={"inflation":"#C85050","debt":"#D48030"},
                           labels={"value":"%","variable":"指標","year":"年"},
                           title="マクロ経済推移 (インフレ率・政府債務)")
            fig2.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)

        # 支持率グラフ
        if 'approval' in df.columns:
            fig3 = px.bar(df, x="year", y="approval", color="approval",
                          color_continuous_scale=["#C85050","#D4A83C","#3AB888"],
                          range_color=[0,100],
                          labels={"approval":"支持率(%)","year":"年"},
                          title="政府支持率推移")
            fig3.update_layout(**PLOT_LAYOUT)
            st.plotly_chart(fig3, use_container_width=True)

        # 履歴テーブル
        st.markdown(c_section("📋 政策実行履歴"), unsafe_allow_html=True)
        th_style = "background:#121F34;color:#2E4060;font-size:10px;padding:8px 10px;text-align:left;border-bottom:1px solid #253858;letter-spacing:.04em"
        td_style = "padding:8px 10px;border-bottom:1px solid #141E38"
        headers = ['年','政策パッケージ','総合国力HI','GDP HI','福祉HI','インフレ率','債務比','支持率']
        tbl = f'<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr>'
        tbl += "".join(f'<th style="{th_style}">{h}</th>' for h in headers)
        tbl += '</tr></thead><tbody>'
        for row in hist:
            n_np  = hi_color(row.get('np',100))
            n_gdp = hi_color(row.get('gdp',100))
            n_wf  = hi_color(row.get('welfare',100))
            n_inf = "#3AB888" if row.get('inflation',5)<5 else "#D4A83C" if row.get('inflation',5)<8 else "#C85050"
            n_dbt = "#D4A83C" if row.get('debt',0)<80 else "#C85050"
            n_ap  = "#3AB888" if row.get('approval',50)>=60 else "#D4A83C"
            tbl += f"""<tr>
  <td style="{td_style};color:#607890">{row['year']}</td>
  <td style="{td_style};color:#C8D8EC">{row.get('policy','')}</td>
  <td style="{td_style};font-weight:700;color:{n_np}">{row.get('np',0)}</td>
  <td style="{td_style};color:{n_gdp}">{row.get('gdp',0)}</td>
  <td style="{td_style};color:{n_wf}">{row.get('welfare',0)}</td>
  <td style="{td_style};color:{n_inf}">{row.get('inflation',0):.1f}%</td>
  <td style="{td_style};color:{n_dbt}">{row.get('debt',0):.1f}%</td>
  <td style="{td_style};color:{n_ap}">{row.get('approval',0)}%</td>
</tr>"""
        tbl += '</tbody></table>'
        st.markdown(tbl, unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="text-align:center;padding:80px 20px;color:#2E4060">
  <div style="font-size:52px;margin-bottom:16px">📊</div>
  <div style="font-size:16px;margin-bottom:8px">データはまだありません</div>
  <div style="font-size:12px">ターンを進めると成長グラフと政策履歴が表示されます</div>
</div>""", unsafe_allow_html=True)
