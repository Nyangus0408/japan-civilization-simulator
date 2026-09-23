import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# ==========================================
# 【データ層】 historical_events.json / 史実データ 相当
# ==========================================
# 1945〜2025年の主要イベントマスター
EVENTS = {
    1947: {"name": "日本国憲法 施行", "desc": "新憲法が施行され、平和主義・民主主義が定着し始めました。"},
    1950: {"name": "朝鮮特需", "desc": "隣国での戦争により、日本の製造業に大量の発注が舞い込みました。"},
    1964: {"name": "東京オリンピック", "desc": "インフラ整備が進み、国際社会への復帰を強く印象付けました。"},
    1973: {"name": "第一次オイルショック", "desc": "中東情勢の悪化により原油価格が急騰。インフレが進行しています。"},
    1985: {"name": "プラザ合意", "desc": "急激な円高が進行し、輸出産業が打撃を受ける一方でバブルの足音が近づいています。"},
    1991: {"name": "バブル崩壊", "desc": "資産価格が急落し、不良債権問題が顕在化し始めました。"},
    2008: {"name": "リーマン・ショック", "desc": "世界的な金融危機により、輸出を中心に日本経済も大きな打撃を受けました。"},
    2011: {"name": "東日本大震災", "desc": "未曾有の大震災と原発事故が発生。サプライチェーンが寸断されました。"},
    2020: {"name": "COVID-19 パンデミック", "desc": "新型感染症の世界的流行により、経済活動が大きく制限されています。"}
}

def generate_hist_data():
    # 1945-2025年の史実ベースラインを自動生成
    data = {}
    for y in range(1945, 2026):
        progress = min(1.0, (y - 1945) / 45.0)
        g = int(0 + 200 * progress if y <= 1990 else 200 + 20 * (y-1990)/35.0)
        w = int(2 + 100 * progress)
        m = int(2 + 40 * progress)
        d = int(30 + 70 * progress)
        t = int(0 + 150 * progress)
        np_val = int(g*0.25 + w*0.15 + m*0.25 + d*0.15 + t*0.20)
        data[y] = {'gdp': g, 'welfare': w, 'military': m, 'diplomacy': d, 'tech': t, 'np': np_val}
    return data

HIST = generate_hist_data()
SCALE = 2.0
W = {'gdp': .25, 'welfare': .15, 'military': .25, 'diplomacy': .15, 'tech': .20}

# ==========================================
# 【エンジン層】 economy.py / core.py 相当
# ==========================================
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
    return round(gNP / max(1, h['np']) * 100)

# ==========================================
# 【AIレイヤー】 advisor.py / cabinet.py 相当
# ==========================================
def call_ai(prompt, as_json=True):
    if "GEMINI_API_KEY" not in st.secrets:
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-3.6-flash')
        resp = model.generate_content(prompt).text
        if as_json:
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0]
            elif "```" in resp: resp = resp.split("```")[1].split("```")[0]
            return json.loads(resp.strip())
        return resp
    except Exception as e:
        st.error(f"AI処理エラー: {e}")
        return None

# ==========================================
# 【UI層】 Streamlit メインアプリ
# ==========================================
st.set_page_config(page_title="日本国家シミュレーション", layout="wide", initial_sidebar_state="collapsed")

# セッションステート初期化（拡張経済モデル変数追加）
if 'year' not in st.session_state:
    st.session_state.year = 1945
    st.session_state.state = {
        'econCap': 0, 'humanCap': 0, 'socialDev': 0, 'milCap': 0, 'diplomNet': 0, 'researchCap': 0,
        'inflation': 5.0, 'debt': 15.0 # 新規追加パラメータ
    }
    st.session_state.history = []
    st.session_state.ai_news = ""
    st.session_state.ai_citizens = {}
    st.session_state.ai_proposal = None
    st.session_state.event_msg = ""

# 現在の数値計算
hi = calc_hi(st.session_state.state)
np_val = calc_np(hi, st.session_state.year)

# UIヘッダー
st.title(f"🇯🇵 日本国家シミュレーション — {st.session_state.year}年")
if st.session_state.year >= 2026:
    st.success("🏁 2025年を突破しました！これ以降はAIによる未知の未来シミュレーションとなります。")

# スマホ閲覧を考慮したコンパクトな指標表示
c1, c2, c3, c4 = st.columns(4)
c1.metric("総合国力", np_val, f"{np_val - 100}% (対史実)")
c2.metric("GDP指数", hi['gdp'])
c3.metric("インフレ率", f"{st.session_state.state['inflation']:.1f}%")
c4.metric("政府債務残高対GDP比", f"{st.session_state.state['debt']:.1f}%")

st.divider()

tab_policy, tab_news, tab_data = st.tabs(["🏛️ 政策とAI閣議", "📰 ニュース・世論", "📊 国家推移データ"])

with tab_policy:
    # 歴史イベントのポップアップ
    if st.session_state.event_msg:
        st.warning(f"🔔 **歴史イベント発生:** {st.session_state.event_msg}")

    st.subheader("💬 AI首相補佐官への指示")
    directive = st.text_area("今期の方針を自然言語で入力してください", placeholder="例：インフレを抑えつつ、地方の教育と医療に予算を回してほしい")
    
    # 政策提案フェーズ
    if st.button("補佐官に政策案を作成させる", type="primary"):
        if directive:
            with st.spinner("AIが現状データを分析し、政策パッケージと閣僚の意見を生成中..."):
                prompt = f"""
                あなたは{st.session_state.year}年の日本のAI首相補佐官です。
                現在の国家状況: GDP指数{hi['gdp']}, インフレ率{st.session_state.state['inflation']}%, 債務比率{st.session_state.state['debt']}%
                首相の指示:「{directive}」
                
                この指示を実現する具体的な政策案と、閣僚たちの反応を生成してください。
                数値を直接変更するのではなく、以下のJSON形式でPythonエンジンへの増減パラメータ(effects)を提案してください。
                
                {{
                  "proposal_name": "政策パッケージ名",
                  "analysis": "現状分析と効果の解説",
                  "cabinet": {{
                    "財務大臣": "財政的な視点での意見",
                    "経産大臣": "産業的な視点での意見",
                    "厚労大臣": "国民生活の視点での意見",
                    "野党党首": "批判的・代替案的な意見"
                  }},
                  "effects": {{
                    "econCap": [経済への影響: -3〜3の整数],
                    "humanCap": [人材・教育への影響: -3〜3の整数],
                    "socialDev": [社会・福祉への影響: -3〜3の整数],
                    "milCap": [軍事への影響: -3〜3の整数],
                    "diplomNet": [外交への影響: -3〜3の整数],
                    "researchCap": [技術への影響: -3〜3の整数],
                    "inflation_change": [インフレ率への影響: -2.0〜2.0の浮動小数点],
                    "debt_change": [債務比率への影響: -5.0〜5.0の浮動小数点]
                  }}
                }}
                """
                resp = call_ai(prompt, as_json=True)
                if resp:
                    st.session_state.ai_proposal = resp
                    st.rerun()
        else:
            st.warning("指示を入力してください。")

    # 政策実行フェーズ
    if st.session_state.ai_proposal:
        prop = st.session_state.ai_proposal
        st.info(f"📋 **提案政策:** {prop.get('proposal_name', '不明')}\n\n**補佐官の分析:** {prop.get('analysis', '')}")
        
        st.write("### 🏛️ 閣僚の意見")
        cab = prop.get('cabinet', {})
        cb1, cb2 = st.columns(2)
        cb1.success(f"**💰 財務大臣:** {cab.get('財務大臣','')}")
        cb2.info(f"**🏭 経産大臣:** {cab.get('経産大臣','')}")
        cb1.warning(f"**🏥 厚労大臣:** {cab.get('厚労大臣','')}")
        cb2.error(f"**🔴 野党党首:** {cab.get('野党党首','')}")

        if st.button("✅ この政策を実行して翌年へ進む", use_container_width=True):
            # パラメータの更新 (AIの提案をPythonエンジンが適用)
            eff = prop.get('effects', {})
            st.session_state.state['econCap'] += eff.get('econCap', 0)
            st.session_state.state['humanCap'] += eff.get('humanCap', 0)
            st.session_state.state['socialDev'] += eff.get('socialDev', 0)
            st.session_state.state['milCap'] += eff.get('milCap', 0)
            st.session_state.state['diplomNet'] += eff.get('diplomNet', 0)
            st.session_state.state['researchCap'] += eff.get('researchCap', 0)
            st.session_state.state['inflation'] += eff.get('inflation_change', 0.0)
            st.session_state.state['debt'] += eff.get('debt_change', 0.0)
            
            # 履歴保存
            st.session_state.history.append({
                'year': st.session_state.year, 'np': np_val, 'gdp': hi['gdp'], 
                'inflation': st.session_state.state['inflation'], 'debt': st.session_state.state['debt']
            })
            
            # 世論とニュースの生成
            with st.spinner("AIが世界の変化と国民の声を演算中..."):
                news_prompt = f"""
                あなたは{st.session_state.year}年の日本です。政府は「{prop.get('proposal_name', '')}」を実行しました。
                以下のJSON形式で時代考証を反映したリアルな反応を生成してください。
                {{
                  "news": "【AI日経速報】見出し\n本文...",
                  "worker": "工場の労働者(30代)の反応",
                  "farmer": "地方の農家(50代)の反応",
                  "student": "都市部の大学生(20代)の反応"
                }}
                """
                news_resp = call_ai(news_prompt, as_json=True)
                if news_resp:
                    st.session_state.ai_news = news_resp.get("news", "")
                    st.session_state.ai_citizens = news_resp
            
            # ターン進行とイベント判定
            st.session_state.year += 1
            st.session_state.ai_proposal = None
            
            if st.session_state.year in EVENTS:
                ev = EVENTS[st.session_state.year]
                st.session_state.event_msg = f"【{ev['name']}】 {ev['desc']}"
            else:
                st.session_state.event_msg = ""
                
            st.rerun()

with tab_news:
    if st.session_state.ai_news:
        st.subheader("📰 AI日本経済新聞")
        st.code(st.session_state.ai_news, language="markdown")
        
        st.subheader("🗣️ AI国民の声")
        # スマホでの視認性を考慮し expander を使用
        with st.expander("👷 製造業労働者の声", expanded=True):
            st.write(st.session_state.ai_citizens.get('worker', ''))
        with st.expander("🌾 地方農家の声", expanded=True):
            st.write(st.session_state.ai_citizens.get('farmer', ''))
        with st.expander("🎓 大学生の声", expanded=True):
            st.write(st.session_state.ai_citizens.get('student', ''))
    else:
        st.write("政策を実行すると、ここにニュースと国民の声が表示されます。")

with tab_data:
    if len(st.session_state.history) > 0:
        df = pd.DataFrame(st.session_state.history)
        fig = px.line(df, x="year", y=["np", "gdp"], markers=True, 
                      labels={"value": "指数", "variable": "指標", "year": "年"},
                      title="国家成長軌跡 (GDP・総合国力)")
        st.plotly_chart(fig, use_container_width=True)
        
        fig2 = px.line(df, x="year", y=["inflation", "debt"], markers=True, 
                      labels={"value": "パーセンテージ(%)", "variable": "指標", "year": "年"},
                      title="マクロ経済推移 (インフレ率・政府債務)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("ターンを進めるとここにグラフが表示されます。")
