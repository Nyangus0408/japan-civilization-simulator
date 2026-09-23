import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# ==========================================
# 1. マスターデータ & シミュレーションエンジン
# ==========================================
Y0, Y1 = 1945, 1975
SCALE = 2.0
W = {'gdp': .25, 'welfare': .15, 'military': .25, 'diplomacy': .15, 'tech': .20}

# 史実データ (1945-1975)
HIST_DATA = [
    (1945,8,15,0,2,30), (1946,7,10,0,2,28), (1947,8,12,0,2,28), (1948,9,13,0,3,29), (1949,10,14,0,3,30),
    (1950,12,18,2,5,31), (1951,14,20,3,12,32), (1952,16,22,5,18,33), (1953,18,24,6,20,35), (1954,19,25,7,22,36),
    (1955,22,28,8,24,38), (1956,25,30,8,30,40), (1957,28,32,9,32,42), (1958,30,33,9,33,43), (1959,34,35,10,35,45),
    (1960,38,38,10,38,48), (1961,43,40,10,40,50), (1962,46,42,10,41,52), (1963,50,44,11,42,54), (1964,55,46,11,46,56),
    (1965,58,48,11,48,58), (1966,63,50,12,49,60), (1967,70,52,12,50,62), (1968,77,54,12,52,64), (1969,84,56,13,54,66),
    (1970,90,58,13,57,68), (1971,93,59,13,59,69), (1972,97,61,14,63,70), (1973,102,60,14,65,72), (1974,99,55,14,66,72),
    (1975,100,57,15,68,73)
]
HIST = {}
for (y, g, w, m, d, t) in HIST_DATA:
    np_val = g*W['gdp'] + w*W['welfare'] + m*W['military'] + d*W['diplomacy'] + t*W['tech']
    HIST[y] = {'gdp': g, 'welfare': w, 'military': m, 'diplomacy': d, 'tech': t, 'np': np_val}

# 利用可能な政策
POLS = [
    {'id':'food', 'name':'食料増産政策', 'cat':'社会', 'era':[1945,1950]},
    {'id':'edu_r', 'name':'教育制度改革', 'cat':'社会', 'era':[1947,1956]},
    {'id':'tilt', 'name':'傾斜生産方式', 'cat':'経済', 'era':[1947,1950]},
    {'id':'dodge', 'name':'ドッジ・ライン推進', 'cat':'経済', 'era':[1949,1951]},
    {'id':'usall', 'name':'日米安保体制強化', 'cat':'外交', 'era':[1951,1975]},
    {'id':'tech_i', 'name':'海外技術導入促進', 'cat':'技術', 'era':[1950,1970]},
    {'id':'heavy', 'name':'重化学工業推進', 'cat':'経済', 'era':[1952,1970]},
    {'id':'soc_s', 'name':'社会保障制度整備', 'cat':'社会', 'era':[1955,1975]},
    {'id':'trade', 'name':'貿易自由化推進', 'cat':'外交', 'era':[1957,1975]},
    {'id':'inc2', 'name':'所得倍増計画', 'cat':'経済', 'era':[1960,1965]},
    {'id':'rd', 'name':'研究開発投資強化', 'cat':'技術', 'era':[1962,1975]},
    {'id':'env', 'name':'環境・公害対策', 'cat':'社会', 'era':[1965,1975]},
    {'id':'asia', 'name':'アジア外交・ODA拡大', 'cat':'外交', 'era':[1965,1975]},
    {'id':'china_p', 'name':'中国関係の先行構築', 'cat':'外交', 'era':[1969,1975]},
    {'id':'enrgy', 'name':'省エネ・産業構造転換', 'cat':'技術', 'era':[1971,1975]},
    {'id':'sdf_b', 'name':'自衛隊整備・防衛強化', 'cat':'防衛', 'era':[1954,1975]},
]

POLS_EFF = {
    'food': {'socialDev': 3}, 'edu_r': {'humanCap': 3}, 'tilt': {'econCap': 5, 'socialDev': -2},
    'dodge': {'econCap': 3}, 'usall': {'diplomNet': 8, 'econCap': 2}, 'tech_i': {'researchCap': 5, 'econCap': 2},
    'heavy': {'econCap': 8, 'socialDev': -3}, 'soc_s': {'socialDev': 5, 'econCap': -1}, 'trade': {'econCap': 3, 'diplomNet': 4},
    'inc2': {'econCap': 10, 'socialDev': 4, 'humanCap': 2}, 'rd': {'researchCap': 5, 'humanCap': 2},
    'env': {'socialDev': 6, 'econCap': -3}, 'asia': {'diplomNet': 8}, 'china_p': {'diplomNet': 12, 'econCap': 4},
    'enrgy': {'researchCap': 5, 'econCap': 3}, 'sdf_b': {'milCap': 7}
}

def calc_hi(d):
    return {
        'gdp': round(100 + (d['econCap']*0.50 + d['humanCap']*0.25 + d['researchCap']*0.15) * SCALE),
        'welfare': round(100 + (d['socialDev']*0.45 + d['humanCap']*0.25 + d['econCap']*0.10) * SCALE),
        'military': round(100 + d['milCap'] * SCALE),
        'diplomacy': round(100 + (d['diplomNet']*0.70 + d['econCap']*0.10) * SCALE),
        'tech': round(100 + (d['researchCap']*0.50 + d['humanCap']*0.35 + d['econCap']*0.15) * SCALE),
    }

def calc_np(hi, yr):
    h = HIST[yr]
    gNP = (h['gdp'] * (hi['gdp']/100) * W['gdp'] +
           h['welfare'] * (hi['welfare']/100) * W['welfare'] +
           h['military'] * (hi['military']/100) * W['military'] +
           h['diplomacy'] * (hi['diplomacy']/100) * W['diplomacy'] +
           h['tech'] * (hi['tech']/100) * W['tech'])
    return round(gNP / h['np'] * 100)

# ==========================================
# 2. AIレイヤー (Gemini API 統合)
# ==========================================
def call_ai(prompt, as_json=True):
    if "GEMINI_API_KEY" not in st.secrets:
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3.6-flash')
        resp = model.generate_content(prompt).text
        if as_json:
            # Markdownのコードブロックをクリーンアップ
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            return json.loads(resp.strip())
        return resp
    except Exception as e:
        st.error(f"AI処理エラー: {e}")
        return None

# ==========================================
# 3. Streamlit UI & State
# ==========================================
st.set_page_config(page_title="AI国家運営シミュレーター", layout="wide", initial_sidebar_state="expanded")

if 'year' not in st.session_state:
    st.session_state.year = Y0
    st.session_state.d = {'econCap':0, 'humanCap':0, 'socialDev':0, 'milCap':0, 'diplomNet':0, 'researchCap':0}
    st.session_state.history = []
    st.session_state.ai_news = ""
    st.session_state.ai_citizens = {}
    st.session_state.cabinet_resp = {}

hi = calc_hi(st.session_state.d)
np_val = calc_np(hi, st.session_state.year)

# ヘッダー領域
st.title(f"🇯🇵 日本再建シミュレーター — {st.session_state.year}年")
cols = st.columns(6)
cols[0].metric("総合国力", np_val, f"{np_val - 100}% (対史実)")
cols[1].metric("GDP", hi['gdp'])
cols[2].metric("国民福祉", hi['welfare'])
cols[3].metric("軍事力", hi['military'])
cols[4].metric("外交力", hi['diplomacy'])
cols[5].metric("技術力", hi['tech'])

st.divider()

# タブ構成
tab_policy, tab_news, tab_data = st.tabs(["🏛️ AI閣議・政策実行", "📰 AIニュース・国民の声", "📊 Historical Index推移"])

# --------- タブ1: AI閣議と政策 ---------
with tab_policy:
    st.subheader("首相の方針指示 (自然言語入力)")
    directive = st.text_area("今期の方針を入力してください", placeholder="例：半導体産業を国内に呼び戻し、同時に社会保障も手厚くしたい")
    
    if st.button("🏛️ 閣議を開催する", type="primary"):
        if directive:
            with st.spinner("AI大臣たちが協議中..."):
                prompt = f"""
                あなたは{st.session_state.year}年の日本の内閣です。首相の指示:「{directive}」
                現在の国家状況: GDP指数{hi['gdp']}, 福祉指数{hi['welfare']} (史実は常に100)
                各大臣の立場で、指示に対する現実的な意見を述べてください。時代考証を踏まえてください。
                以下のJSONのみを出力してください。
                {{"官房長官": "...", "財務大臣": "...", "経産大臣": "...", "厚労大臣": "...", "野党党首": "..."}}
                """
                resp = call_ai(prompt, as_json=True)
                if resp:
                    st.session_state.cabinet_resp = resp
        else:
            st.warning("方針を入力してください。")

    if st.session_state.cabinet_resp:
        c1, c2, c3 = st.columns(3)
        c1.info(f"**🏛️ 官房長官:**\n\n{st.session_state.cabinet_resp.get('官房長官','')}")
        c2.warning(f"**💰 財務大臣:**\n\n{st.session_state.cabinet_resp.get('財務大臣','')}")
        c3.success(f"**🏭 経産大臣:**\n\n{st.session_state.cabinet_resp.get('経産大臣','')}")
        c1.error(f"**🏥 厚労大臣:**\n\n{st.session_state.cabinet_resp.get('厚労大臣','')}")
        c2.secondary(f"**🔴 野党党首:**\n\n{st.session_state.cabinet_resp.get('野党党首','')}")
    
    st.subheader("政策の実行")
    # 選択可能な政策をフィルタ
    avail_pols = [p for p in POLS if p['era'][0] <= st.session_state.year <= p['era'][1]]
    selected_pols = st.multiselect("方針を踏まえ、実行する政策パッケージを選択してください", options=[p['id'] for p in avail_pols], format_func=lambda x: next(p['name'] for p in avail_pols if p['id'] == x))

    if st.button("次の年へ進む ➔", use_container_width=True):
        # 政策の適用
        pol_names = []
        for p_id in selected_pols:
            effs = POLS_EFF.get(p_id, {})
            for k, v in effs.items():
                st.session_state.d[k] += v
            pol_names.append(next(p['name'] for p in avail_pols if p['id'] == p_id))
            
        st.session_state.history.append({
            'year': st.session_state.year, 'np': np_val, 'gdp': hi['gdp'], 'welfare': hi['welfare']
        })
        
        # 次のターンに向けたAI生成（ニュース・国民の声）
        with st.spinner("AIが世界の変化を演算中..."):
            p_str = "、".join(pol_names) if pol_names else "特になし"
            news_prompt = f"""
            あなたは{st.session_state.year}年の日本に生きる人々です。政府は今年、以下の政策を実行しました: {p_str}
            以下のJSON形式でリアルな反応を生成してください。時代考証（白黒テレビ、石油危機など）を反映させてください。
            {{
              "news": "【AI日経速報】見出し\n本文...",
              "worker": "工場の労働者(30代)の反応",
              "farmer": "農家(50代)の反応",
              "student": "大学生(20代)の反応"
            }}
            """
            news_resp = call_ai(news_prompt, as_json=True)
            if news_resp:
                st.session_state.ai_news = news_resp.get("news", "")
                st.session_state.ai_citizens = news_resp
        
        st.session_state.year += 1
        st.session_state.cabinet_resp = {}
        st.rerun()

# --------- タブ2: AIニュースと国民の声 ---------
with tab_news:
    if st.session_state.ai_news:
        st.subheader("📰 AI日本経済新聞")
        st.code(st.session_state.ai_news, language="markdown")
        
        st.subheader("🗣️ AI国民の声")
        colA, colB, colC = st.columns(3)
        colA.info(f"**👷 製造業労働者:**\n\n{st.session_state.ai_citizens.get('worker', '')}")
        colB.success(f"**🌾 農家:**\n\n{st.session_state.ai_citizens.get('farmer', '')}")
        colC.warning(f"**🎓 大学生:**\n\n{st.session_state.ai_citizens.get('student', '')}")
    else:
        st.write("まだ大きなニュースはありません。「次の年へ進む」とAIが世論を生成します。")

# --------- タブ3: データ推移 ---------
with tab_data:
    if len(st.session_state.history) > 0:
        df = pd.DataFrame(st.session_state.history)
        fig = px.line(df, x="year", y=["np", "gdp", "welfare"], markers=True, 
                      labels={"value": "Historical Index (史実=100)", "variable": "指標", "year": "年"},
                      title="国家の成長軌跡")
        fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="史実基準(100)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("ターンを進めるとここにグラフが表示されます。")
