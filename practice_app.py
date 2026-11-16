# =========================================================
# 실전 보고서 실습 코치 (모듈 1~3)
# 교육생이 '데이터 질문 카드 → 인사이트 보드 → 한 장 보고서 + 팩트체크 표'를
# 11단계로 실습합니다. 앞 단계 결과는 다음 단계로 자동으로 이어집니다.
# =========================================================
import io
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
DATA_DIR = BASE / "practice_data"
DEFAULT_MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="실전 보고서 실습 코치", layout="wide")

# ---------------------------------------------------------
# 과정 구성
# ---------------------------------------------------------
SCENARIOS = {
    "마케팅 · 월간 회원 현황 보고": {
        "file": "marketing_members_2025.csv", "task": "월간 회원 현황 보고서", "people": "마케팅 팀장"},
    "영업 · 하반기 지역별 매출 점검": {
        "file": "sales_region_2025H2.csv", "task": "하반기 지역별 매출 점검 보고서", "people": "영업본부장"},
    "HR · 신입사원 조기 퇴사 현황": {
        "file": "hr_newhire_2023_2024.csv", "task": "신입사원 조기 퇴사 현황 보고", "people": "인사팀장"},
    "CS · 3분기 고객 불만 유형 분석": {
        "file": "cs_complaints_2025.csv", "task": "3분기 고객 불만 유형 분석 보고서", "people": "고객경험실장"},
    "직접 입력 (내 과제 · 내 데이터)": {"file": None, "task": "", "people": ""},
}

STEPS = [
    ("1-1", "현업 과제 정하기"),
    ("1-2", "SPICE로 정리하기"),
    ("1-3", "데이터 질문 카드 완성"),
    ("2-1", "보고서 뼈대 PPM"),
    ("2-2", "데이터 준비 · 정리"),
    ("2-3", "하위 질문별 분석"),
    ("2-4", "문제 정의 · 인사이트 보드"),
    ("3-1", "SCQA 스토리"),
    ("3-2", "근거 보강 · 팩트체크 표"),
    ("3-3", "초안 작성"),
    ("3-4", "퇴고 · 최종 점검"),
]
TITLE = dict(STEPS)
IDS = [s for s, _ in STEPS]
MODULE_NAME = {"1": "모듈 1 · 좋은 보고서는 좋은 질문에서 시작된다",
               "2": "모듈 2 · AI와 함께 데이터를 인사이트로 바꾸기",
               "3": "모듈 3 · AI와 함께 설득력 있는 보고서 완성하기"}
TIPS = {
    "1-1": "일의 시작은 두 가지 맥락적 질문입니다. ‘이 일을 왜 하는가?’와 ‘무엇을 알아내야 하는가?’",
    "1-2": "SPICE로 질문의 방향을 구체화합니다. S·P·C는 지금 아는 것으로, I·E는 가설로 적어 두세요.",
    "1-3": "핵심 질문 1개를 하위 질문 3개로 쪼개고, 질문마다 필요한 데이터를 적습니다.",
    "2-1": "PPM은 보고서의 설계도입니다. 메시지는 아직 ‘가설’이어도 괜찮습니다.",
    "2-2": "요리는 손질부터, 분석은 전처리부터. 정리 기록을 확인하고 원본 숫자 2개를 직접 대조하세요.",
    "2-3": "계산은 파이썬이, 해석은 AI가 합니다. AI의 해석이 표의 숫자와 맞는지 확인하고 내 문장으로 고르세요.",
    "2-4": "문제란 목표와 현실 사이의 차이(Gap)입니다. 현상의 나열이 아니라 차이 + 해석 + 해결 방향을 쓰세요.",
    "3-1": "SCQA로 설득의 시나리오를 만듭니다. 이미 가진 A(핵심 메시지)에 도달하는 길을 설계하세요.",
    "3-2": "보고서의 숫자는 모두 팩트체크 표에 남깁니다. ‘확인 필요’가 남은 숫자는 보고서에 쓰지 않습니다.",
    "3-3": "흩어진 결과물을 한 문서(마스터 소스)로 모아, 목차와 숫자를 지키며 초안을 씁니다.",
    "3-4": "결론형 제목으로 퇴고하고, 환각 검사와 예상 질문으로 마지막 점검을 합니다.",
}
CHECK_STATUS = ["확인 필요", "원본 대조", "링크 확인"]
TIME_HINTS = ("월", "날짜", "일자", "연도", "기간", "시기", "분기", "반기", "date", "month")
MISSING_WORDS = {"", "-", "모름", "N/A", "n/a", "NA", "nan", "None", "?"}
TOTAL_WORDS = {"합계", "총계", "소계", "Total", "total"}

COACH = """너는 '데이터 분석 에이전트로 완성하는 실전 보고서' 과정의 실습 코치야.
교육생은 생성형 AI가 처음인 일반 직장인이다.
원칙:
1. 교육생이 쓴 내용에서 잘한 점을 먼저 한 줄로 짚고, 고칠 점은 최대 3가지만 구체적으로 말한다.
2. 피드백을 요청받으면 답을 대신 써 주지 말고 질문과 짧은 예시로 이끈다. '초안 제안'을 요청받았을 때만 직접 써 준다.
3. 숫자는 제공된 데이터와 표에 있는 값만 쓴다. 없으면 '확인 필요'라고 쓴다.
4. 쉬운 한국어, 짧은 개조식, 마크다운으로 답한다. 전체 길이는 화면 한 장을 넘기지 않는다.
5. 과정의 용어(SPICE, PPM, Gap, SCQA, 주·문·제·작, 팩트체크 표)를 그대로 쓴다."""

WRITER = """너는 전략기획팀의 보고서 작성 전문가야.
규칙: 주어진 마스터 소스 밖의 사실이나 숫자를 만들지 않는다. 숫자는 원문 그대로 쓰고 출처를 괄호로 단다.
팩트체크 표에서 '확인 필요'인 숫자는 쓰지 않는다. 개조식, 마크다운으로 쓴다."""


# ---------------------------------------------------------
# 작업 상태 (교육생 한 명의 실습 기록)
# ---------------------------------------------------------
def new_work():
    return {
        "version": 1, "scenario": list(SCENARIOS)[0], "name": "", "task": "", "why": "", "what": "",
        "spice": {"S": "", "P": "", "I": "", "C": "", "E": ""},
        "core_q": "", "subs": [{"q": "", "data": "", "where": ""} for _ in range(3)],
        "ppm": {"purpose": "", "people": "", "message": ""},
        "data_name": "", "data_csv": "", "clean_log": [],
        "analyses": [{} for _ in range(3)],
        "gap_type": "집단의 차이", "problem": "", "final_message": "",
        "scqa": {"S": "", "C": "", "Q": "", "A": ""},
        "facts": [], "draft": "", "revised": "",
        "persona": {"title": "", "criteria": "", "questions": ""},
        "checks": {}, "done": {}, "ai": {}, "prompts": {},
    }


if "W" not in st.session_state:
    st.session_state.W = new_work()
W = st.session_state.W
WIDGET_PREFIXES = ("f_", "a0_", "a1_", "a2_", "chk_", "d_", "sel_")


def gp(path):
    cur = W
    for p in path.split("."):
        cur = cur[int(p)] if isinstance(cur, list) else cur.setdefault(p, "")
    return cur


def sp(path, value):
    parts = path.split(".")
    cur = W
    for p in parts[:-1]:
        cur = cur[int(p)] if isinstance(cur, list) else cur[p]
    if isinstance(cur, list):
        cur[int(parts[-1])] = value
    else:
        cur[parts[-1]] = value


def field(label, path, area=False, height=110, placeholder="", help=None):
    """작업 상태와 연결된 입력칸. 입력한 내용은 바로 저장됩니다."""
    key = "f_" + path
    if key not in st.session_state:
        st.session_state[key] = gp(path)
    if area:
        value = st.text_area(label, key=key, height=height, placeholder=placeholder, help=help)
    else:
        value = st.text_input(label, key=key, placeholder=placeholder, help=help)
    sp(path, value)
    return value


def prefill(path, value):
    """앞 단계의 내용을 다음 단계의 빈칸에 미리 채웁니다."""
    if value and not gp(path):
        sp(path, value)
        if not st.session_state.get("f_" + path):
            st.session_state["f_" + path] = value


def load_work():
    f = st.session_state.get("sel_loader")
    if f is None:
        return
    try:
        data = json.loads(f.getvalue().decode("utf-8"))
        merged = new_work()
        merged.update(data)
        st.session_state.W = merged
        for k in list(st.session_state.keys()):
            if k.startswith(WIDGET_PREFIXES) and k != "sel_loader":
                del st.session_state[k]
        st.session_state.pop("df", None)
        st.session_state.pop("facts_base", None)
        st.session_state.step = next((s for s in IDS if not merged["done"].get(s)), IDS[-1])
        st.session_state.load_msg = "저장한 작업을 불러왔습니다."
    except Exception as e:  # noqa: BLE001
        st.session_state.load_msg = f"불러오기에 실패했습니다: {e}"


# ---------------------------------------------------------
# AI
# ---------------------------------------------------------
def get_api_key():
    key = st.session_state.get("user_key")
    if key:
        return key
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001
        key = None
    return key or os.environ.get("GEMINI_API_KEY")


def ask_ai(prompt, system=COACH, temperature=0.3):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(
        model=st.session_state.get("model") or DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
    )
    return response.text or ""


def call_ai(slot, prompt, system=COACH):
    """AI를 부르고 결과와 프롬프트를 작업 기록에 남깁니다. 성공하면 결과를 돌려줍니다."""
    if not get_api_key():
        st.warning("API 키가 없습니다. 왼쪽 ‘AI 설정’에서 키를 넣거나 강사에게 문의하세요.")
        return None
    W["prompts"][slot] = prompt
    with st.spinner("AI 코치가 읽고 있습니다..."):
        try:
            W["ai"][slot] = ask_ai(prompt, system)
            return W["ai"][slot]
        except Exception as e:  # noqa: BLE001
            st.error(f"AI를 부르는 중 오류가 났습니다: {e}")
            return None


def show_ai(slot, title="AI 코치"):
    if W["ai"].get(slot):
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.markdown(W["ai"][slot])
        if W["prompts"].get(slot):
            with st.expander("AI에게 실제로 보낸 프롬프트 보기"):
                st.code(W["prompts"][slot], language=None)


def ai_button(label, slot, prompt_fn, system=COACH, title="AI 코치"):
    if st.button(label, key=f"btn_{slot}"):
        call_ai(slot, prompt_fn(), system)
    show_ai(slot, title)


# ---------------------------------------------------------
# 데이터
# ---------------------------------------------------------
def read_table(file, name):
    if name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file, dtype=str).fillna("")
    for enc in ("utf-8-sig", "cp949"):
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            return pd.read_csv(file, encoding=enc, dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            continue
    raise ValueError("파일을 읽지 못했습니다. CSV를 UTF-8 또는 CP949로 저장해 주세요.")


def clean(raw):
    """합계·중복 행 제외, 숫자 변환, 빈칸 처리, 이상치 의심 표시. 바꾼 내용을 기록합니다."""
    log = []
    text = raw.apply(lambda col: col.astype(str).str.strip())
    total_mask = text.isin(TOTAL_WORDS).any(axis=1)
    if total_mask.any():
        log.append(f"합계/총계 행 {int(total_mask.sum())}개를 계산에서 뺐습니다.")
        text = text[~total_mask]
    dup_mask = text.duplicated()
    if dup_mask.any():
        log.append(f"완전히 같은 중복 행 {int(dup_mask.sum())}개를 뺐습니다.")
        text = text[~dup_mask]
    df = text.mask(text.isin(MISSING_WORDS))
    for col in df.columns:
        values = df[col].dropna()
        if values.empty:
            continue
        numbers = pd.to_numeric(values.str.replace(",", "", regex=False), errors="coerce")
        if numbers.notna().mean() >= 0.8:
            bad = int(numbers.isna().sum())
            df[col] = pd.to_numeric(df[col].str.replace(",", "", regex=False), errors="coerce")
            if bad:
                log.append(f"'{col}' 열의 숫자가 아닌 값 {bad}개를 빈칸으로 바꿨습니다.")
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        if n_missing:
            log.append(f"'{col}' 열에 빈칸이 {n_missing}개 있습니다(계산에서 제외).")
    for col in df.select_dtypes("number").columns:
        s = df[col].dropna()
        if len(s) < 8:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        outliers = s[s > q3 + 3 * (q3 - q1)]
        if len(outliers):
            log.append(f"'{col}' 열에 이상치로 의심되는 값이 있습니다: {', '.join(str(v) for v in outliers.tolist())}")
    return df.reset_index(drop=True), log


def get_df():
    if "df" in st.session_state:
        return st.session_state.df
    if W["data_csv"]:
        st.session_state.df = pd.read_csv(io.StringIO(W["data_csv"]))
        return st.session_state.df
    return None


def set_df(raw, name):
    df, log = clean(raw)
    st.session_state.df = df
    W["data_name"], W["data_csv"], W["clean_log"] = name, df.to_csv(index=False), log
    W["analyses"] = [{} for _ in range(3)]
    for k in list(st.session_state.keys()):
        if k.startswith(("a0_", "a1_", "a2_", "f_analyses")):
            del st.session_state[k]


def is_time(col):
    return any(h in str(col) for h in TIME_HINTS)


def compute(df, keys, values, agg, ratio):
    grouped = df.dropna(subset=keys).groupby(keys)[values]
    table = (grouped.sum() if agg == "합계" else grouped.mean().round(2)).reset_index()
    if ratio and ratio[0] in table and ratio[1] in table and ratio[0] != ratio[1]:
        table[f"{ratio[0]}÷{ratio[1]}(%)"] = (table[ratio[0]] / table[ratio[1]] * 100).round(1)
    if len(keys) == 1 and is_time(keys[0]):
        for v in values:
            table[f"{v}_전기대비"] = table[v].diff()
    return table


def draw_chart(a):
    if not a.get("table_csv") or a.get("chart") == "표만":
        return
    table = pd.read_csv(io.StringIO(a["table_csv"]))
    keys, plot = a["keys"], a.get("plot")
    if plot not in table.columns:
        return
    if len(keys) == 1:
        data = table.set_index(keys[0])[[plot]]
    else:
        data = table.pivot_table(index=keys[0], columns=keys[1], values=plot, aggfunc="sum")
    if a.get("chart") == "꺾은선":
        st.line_chart(data)
    else:
        st.bar_chart(data)


def md_table(rows, cols):
    """표를 마크다운으로 바꿉니다."""
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/") for c in cols) + " |")
    return "\n".join(out)


def card_md():
    s = W["spice"]
    subs = [x for x in W["subs"] if x["q"].strip()]
    return "\n".join([
        f"# 데이터 질문 카드 — {W['task']}", "",
        f"- 작성자: {W['name'] or '-'}", f"- 이 일을 왜 하는가: {W['why']}", f"- 무엇을 알아내야 하는가: {W['what']}", "",
        "## SPICE",
        md_table([{"구분": k, "내용": s[k]} for k in ["S", "P", "I", "C", "E"]], ["구분", "내용"]), "",
        f"## 핵심 질문\n{W['core_q']}", "",
        "## 하위 질문과 필요한 데이터",
        md_table([{"하위 질문": x["q"], "필요한 데이터": x["data"], "구하는 곳": x["where"]} for x in subs],
                 ["하위 질문", "필요한 데이터", "구하는 곳"]),
    ])


def board_md():
    p = W["ppm"]
    lines = [f"# 인사이트 보드 — {W['task']}", "", "## ① 보고서 뼈대 (PPM)",
             f"- 목적: {p['purpose']}", f"- 청중: {p['people']}", f"- 메시지: {W['final_message'] or p['message']}", "",
             "## ② 핵심 차트"]
    for i, a in enumerate(W["analyses"]):
        if a.get("table_csv") and a.get("use", True):
            lines += [f"### {a.get('headline') or W['subs'][i]['q']}",
                      f"- 하위 질문: {W['subs'][i]['q']}", f"- 발견: {a.get('finding', '')}", "",
                      "```csv", a["table_csv"].strip(), "```", ""]
    lines += ["## ③ 핵심 메시지", f"- 차이 유형: {W['gap_type']}", f"- 문제 정의: {W['problem']}",
              f"- 핵심 메시지: {W['final_message'] or p['message']}"]
    return "\n".join(lines)


def facts_md():
    return md_table(W["facts"], ["주장", "숫자", "출처", "확인"]) if W["facts"] else "(작성 전)"


def master_source():
    sc = W["scqa"]
    return "\n\n".join([
        card_md(), board_md(),
        f"# SCQA\n- S 상황: {sc['S']}\n- C 한계: {sc['C']}\n- Q 핵심 질문: {sc['Q']}\n- A 해답: {sc['A']}",
        "# 팩트체크 표\n" + facts_md(),
    ])


# ---------------------------------------------------------
# 화면 공통
# ---------------------------------------------------------
def go_next(sid):
    W["done"][sid] = True
    i = IDS.index(sid)
    if i + 1 < len(IDS):
        st.session_state.step = IDS[i + 1]


def step_footer(sid):
    st.divider()
    last = IDS.index(sid) + 1 == len(IDS)
    st.button("이 단계 완료" if last else "이 단계 완료 → 다음 단계", type="primary",
              key=f"next_{sid}", on_click=go_next, args=(sid,))


def header(sid):
    st.caption(MODULE_NAME[sid[0]])
    st.header(f"{sid}  {TITLE[sid]}")
    st.info(TIPS[sid])


def need(condition, message):
    if not condition:
        st.warning(message)
    return condition


# ---------------------------------------------------------
# 사이드바
# ---------------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = IDS[0]
st.session_state.setdefault("model", DEFAULT_MODEL)

with st.sidebar:
    st.title("실전 보고서 실습 코치")
    n_done = sum(1 for s in IDS if W["done"].get(s))
    st.progress(n_done / len(IDS), text=f"진행 {n_done} / {len(IDS)} 단계")
    st.radio("실습 단계", IDS, key="step",
             format_func=lambda s: f"{s}  {TITLE[s]}" + ("  ✓" if W["done"].get(s) else ""))
    st.divider()
    st.download_button("내 작업 저장 (.json)", data=json.dumps(W, ensure_ascii=False, indent=1),
                       file_name=f"실습작업_{W['name'] or '교육생'}_{datetime.now():%m%d_%H%M}.json",
                       mime="application/json", help="창을 닫거나 새로고침하면 작업이 사라집니다. 자주 저장하세요.")
    st.file_uploader("저장한 작업 불러오기", type=["json"], key="sel_loader", on_change=load_work)
    if st.session_state.get("load_msg"):
        st.caption(st.session_state.pop("load_msg"))
    with st.expander("AI 설정"):
        st.text_input("AI 모델 이름", key="model")
        st.text_input("내 Gemini API 키 (선택)", key="user_key", type="password",
                      help="강사가 준비한 키가 있으면 비워 두세요.")
        st.caption("API 키 상태: " + ("준비됨" if get_api_key() else "없음"))

step = st.session_state.step
header(step)

# ---------------------------------------------------------
# 모듈 1
# ---------------------------------------------------------
if step == "1-1":
    def on_scenario():
        W["scenario"] = st.session_state.sel_scenario
        sc = SCENARIOS[W["scenario"]]
        for path, value in (("task", sc["task"]), ("ppm.people", sc["people"])):
            sp(path, value)
            st.session_state["f_" + path] = value
        st.session_state.pop("df", None)
        W["data_csv"], W["data_name"], W["clean_log"] = "", "", []

    st.session_state.setdefault("sel_scenario", W["scenario"])
    st.selectbox("실습 시나리오", list(SCENARIOS), key="sel_scenario", on_change=on_scenario,
                 help="직무별 실습 데이터가 준비되어 있습니다. 내 과제로 하려면 ‘직접 입력’을 고르세요.")
    prefill("task", SCENARIOS[W["scenario"]]["task"])
    prefill("ppm.people", SCENARIOS[W["scenario"]]["people"])
    c1, c2 = st.columns([1, 2])
    with c1:
        field("이름 (선택)", "name")
    with c2:
        field("현업 과제 (한 줄)", "task", placeholder="예) 3분기 고객 불만 유형 분석 보고서")
    field("Q1. 이 일을 왜 하는가?", "why", area=True, placeholder="예) 다음 분기 CS 인력 배치와 개선 과제를 정하기 위해")
    field("Q2. 무엇을 알아내야 하는가?", "what", area=True, placeholder="예) 어떤 불만이 늘었고, 왜 늘었고, 무엇부터 고쳐야 하는지")
    ai_button("AI 코치에게 피드백 받기", "1-1", lambda: f"""[현업 과제]
{W['task']}
[Q1. 이 일을 왜 하는가?]
{W['why']}
[Q2. 무엇을 알아내야 하는가?]
{W['what']}

[요청]
1. Q1과 Q2가 구체적인지 한 줄씩 평가해 줘.
2. 이 과제를 더 선명하게 만들 '전제 조건' 질문(누가, 왜, 어떤 조건에서)을 3개 던져 줘.
3. 답을 대신 써 주지는 마.""")
    step_footer(step)

elif step == "1-2":
    st.write(f"**현업 과제:** {W['task'] or '(1-1에서 입력하세요)'}")
    labels = {
        "S": ("S 상황", "지금 시장과 우리 상황은 어떠한가?"),
        "P": ("P 목적", "이 보고를 왜 하는가? 목표는?"),
        "I": ("I 핵심발견 (가설, 비워도 됨)", "데이터가 말할 것 같은 핵심 이야기는? → 모듈 2에서 확인"),
        "C": ("C 고객", "보고를 받는 사람은 누구이고, 무엇을 고민하는가?"),
        "E": ("E 기대효과 (가설, 비워도 됨)", "실행 후 무엇이 구체적으로 달라지나? → 모듈 3에서 확인"),
    }
    prefill("spice.P", W["why"])
    for k in ["S", "P", "C", "I", "E"]:
        field(labels[k][0], f"spice.{k}", area=True, height=80, placeholder=labels[k][1])
    ai_button("AI 코치에게 피드백 받기", "1-2", lambda: f"""[현업 과제] {W['task']}
[SPICE]
S 상황: {W['spice']['S']}
P 목적: {W['spice']['P']}
I 핵심발견(가설): {W['spice']['I']}
C 고객: {W['spice']['C']}
E 기대효과(가설): {W['spice']['E']}

[요청]
1. 다섯 항목을 '좋음 / 보완' 으로 판정한 표를 만들어 줘. (항목 | 판정 | 한 줄 이유)
2. 보완이 필요한 항목마다 'AI가 묻지 않는 질문'을 하나씩 던져 줘. 우리 회사·우리 고객의 특수한 상황을 묻는 질문이어야 해.
3. 답을 대신 써 주지는 마.""")
    step_footer(step)

elif step == "1-3":
    sc = SCENARIOS[W["scenario"]]
    if sc["file"]:
        cols = pd.read_csv(DATA_DIR / sc["file"], encoding="utf-8-sig", nrows=1).columns.tolist()
        st.caption("실습 데이터에 있는 열: " + ", ".join(cols))
    field("핵심 질문 (이 보고서가 답해야 할 단 하나의 질문)", "core_q", area=True, height=80,
          placeholder="예) 고객을 늘리려면 신규 유입과 이탈 방지 중 어디에 집중해야 할까?")
    st.markdown("**하위 질문 3개와 필요한 데이터**")
    for i in range(3):
        c1, c2, c3 = st.columns([3, 2, 2])
        with c1:
            field(f"하위 질문 {'①②③'[i]}", f"subs.{i}.q", placeholder="예) 최근 6개월 순증감 추이는?")
        with c2:
            field("필요한 데이터", f"subs.{i}.data", placeholder="예) 월별 신규·이탈 수")
        with c3:
            field("구하는 곳", f"subs.{i}.where", placeholder="예) 회원 관리 시스템")
    ai_button("AI 코치에게 질문 카드 점검받기", "1-3", lambda: f"""{card_md()}

[실습 데이터의 열]
{', '.join(cols) if sc['file'] else '(교육생이 자기 데이터를 사용)'}

[요청] 아래 5가지 기준으로 이 질문 카드를 점검해 줘.
1. 핵심 질문은 한 문장이고, 보고를 받는 사람이 궁금해할 질문인가?
2. 하위 질문 3개에 답하면 핵심 질문의 답이 나오는가?
3. 하위 질문은 숫자·비교·추이처럼 데이터로 답할 수 있는 형태인가?
4. 질문에 대상·기간·기준이 들어 있는가?
5. 필요한 데이터를 실제로 구할 수 있는가? (실습 데이터의 열로 답할 수 있는지도 봐 줘)
형식: 기준 | 통과/보완 | 한 줄 코멘트 의 표, 그 아래에 가장 먼저 고칠 점 2가지.""")
    with st.expander("완성된 데이터 질문 카드 미리보기", expanded=False):
        st.markdown(card_md())
    st.download_button("데이터 질문 카드 내려받기 (.md)", card_md(), file_name="데이터질문카드.md", mime="text/markdown")
    step_footer(step)

# ---------------------------------------------------------
# 모듈 2
# ---------------------------------------------------------
elif step == "2-1":
    prefill("ppm.purpose", W["spice"]["P"])
    prefill("ppm.people", W["spice"]["C"])
    st.write(f"**핵심 질문:** {W['core_q'] or '(1-3에서 입력하세요)'}")
    field("Purpose 목적 — 어떤 결정을 돕는 보고서인가?", "ppm.purpose", area=True, height=80)
    field("People 청중 — 누가 읽고, 무엇에 민감한가?", "ppm.people", area=True, height=80)
    field("Message 핵심 메시지 (가설) — 그래서 하고 싶은 말은?", "ppm.message", area=True, height=80,
          placeholder="예) 신규보다 이탈 방지에 예산을 집중해야 고객이 늘어난다")
    ai_button("AI 코치에게 피드백 받기", "2-1", lambda: f"""[핵심 질문] {W['core_q']}
[PPM]
Purpose 목적: {W['ppm']['purpose']}
People 청중: {W['ppm']['people']}
Message 메시지(가설): {W['ppm']['message']}

[요청]
1. 메시지가 좋은 메시지의 3조건(명확하다 / 행동·방향이 있다 / 데이터에 기반한다)을 갖췄는지 조건별로 판정해 줘.
2. 청중이 이 보고서에서 가장 먼저 물어볼 질문 2개를 알려 줘.
3. 고쳐 쓴 '예시' 메시지를 1개만 보여 줘. 예시라고 꼭 표시해.""")
    step_footer(step)

elif step == "2-2":
    sc = SCENARIOS[W["scenario"]]
    st.warning("회사의 개인정보·기밀 데이터는 올리지 마세요. 올린 데이터는 AI 회사 서버로 전송됩니다.")
    options = (["시나리오 실습 데이터"] if sc["file"] else []) + ["내 파일 올리기"]
    src = st.radio("데이터 가져오기", options, key="d_src", horizontal=True)
    if src == "시나리오 실습 데이터":
        st.caption(f"파일: {sc['file']}")
        if st.button("이 데이터로 정리하기", key="d_load_sample"):
            set_df(read_table(DATA_DIR / sc["file"], sc["file"]), sc["file"])
    else:
        up = st.file_uploader("CSV 또는 엑셀 파일", type=["csv", "xlsx"], key="d_upload")
        if up is not None and st.button("이 파일로 정리하기", key="d_load_upload"):
            try:
                set_df(read_table(up, up.name), up.name)
            except Exception as e:  # noqa: BLE001
                st.error(f"데이터를 읽는 중 오류가 났습니다: {e}")
    df = get_df()
    if df is not None:
        st.success(f"정리된 데이터: {W['data_name']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("행", len(df))
        c2.metric("열", df.shape[1])
        c3.metric("빈칸", int(df.isna().sum().sum()))
        st.dataframe(df, height=260)
        with st.expander(f"데이터 정리 기록 ({len(W['clean_log'])}건)", expanded=bool(W["clean_log"])):
            for item in W["clean_log"] or ["정리할 내용이 없었습니다."]:
                st.write("- " + item)
        st.session_state.setdefault("chk_data", W["checks"].get("data_verified", False))
        W["checks"]["data_verified"] = st.checkbox("원본 파일에서 숫자 2개를 골라 위 표와 직접 대조했다", key="chk_data")
        ai_button("AI에게 데이터 요약받기", "2-2", lambda: f"""[하위 질문]
{chr(10).join('- ' + x['q'] for x in W['subs'] if x['q'])}
[데이터 정리 기록]
{chr(10).join('- ' + x for x in W['clean_log']) or '- 없음'}
[데이터 앞부분 (CSV)]
{df.head(40).to_csv(index=False)}
[열별 빈칸 수]
{df.isna().sum().to_string()}

[요청]
1. 이 데이터의 생김새를 3줄로 요약해 줘(무엇에 대한 데이터인지, 기간, 단위).
2. 하위 질문마다 '기준 열'과 '값 열'로 무엇을 고르면 좋을지 표로 알려 줘. (하위 질문 | 기준 열 | 값 열 | 비율 계산이 필요하면 분자÷분모)
3. 분석 전에 주의할 점을 최대 2개 알려 줘.""")
    step_footer(step)

elif step == "2-3":
    df = get_df()
    if need(df is not None, "먼저 2-2에서 데이터를 정리해 주세요."):
        text_cols = [c for c in df.columns if c not in df.select_dtypes("number").columns]
        num_cols = df.select_dtypes("number").columns.tolist()
        if not need(text_cols and num_cols, "기준이 될 글자 열과 계산할 숫자 열이 모두 있어야 합니다."):
            st.stop()
        tabs = st.tabs([f"하위 질문 {'①②③'[i]}" for i in range(3)])
        for i, tab in enumerate(tabs):
            with tab:
                a = W["analyses"][i]
                q = W["subs"][i]["q"] or f"(1-3에서 하위 질문 {'①②③'[i]}을 입력하세요)"
                st.markdown(f"**{q}**")
                c1, c2, c3 = st.columns(3)
                keys = c1.multiselect("기준 열 (묶을 기준, 최대 2개)", text_cols, max_selections=2,
                                      default=[k for k in a.get("keys", text_cols[:1]) if k in text_cols],
                                      key=f"a{i}_keys")
                values = c2.multiselect("값 열 (계산할 숫자)", num_cols,
                                        default=[v for v in a.get("values", num_cols[:1]) if v in num_cols],
                                        key=f"a{i}_values")
                agg = c3.radio("계산 방법", ["합계", "평균"], horizontal=True, key=f"a{i}_agg",
                               index=["합계", "평균"].index(a.get("agg", "합계")))
                use_ratio = st.checkbox("비율 열 추가 (예: 이탈 ÷ 신규, 퇴사자 ÷ 입사자)", key=f"a{i}_useratio",
                                        value=bool(a.get("ratio")))
                ratio = None
                if use_ratio and len(values) >= 2:
                    r1, r2 = st.columns(2)
                    # 기본값: 합계가 작은 열을 분자로 (예: 퇴사자 ÷ 입사자, 매출 ÷ 목표)
                    old = a.get("ratio") or sorted(values[:2], key=lambda c: df[c].sum())
                    num = r1.selectbox("분자", values, key=f"a{i}_num",
                                       index=values.index(old[0]) if old[0] in values else 0)
                    den = r2.selectbox("분모", values, key=f"a{i}_den",
                                       index=values.index(old[1]) if old[1] in values else min(1, len(values) - 1))
                    ratio = [num, den]
                elif use_ratio:
                    st.caption("비율을 계산하려면 값 열을 2개 이상 고르세요.")
                if not (keys and values):
                    st.caption("기준 열과 값 열을 고르면 파이썬이 집계표를 계산합니다.")
                    continue
                table = compute(df, keys, values, agg, ratio)
                st.dataframe(table, hide_index=True)
                plot_options = [c for c in table.columns if c not in keys]
                p1, p2 = st.columns(2)
                plot = p1.selectbox("차트에 그릴 값", plot_options, key=f"a{i}_plot",
                                    index=plot_options.index(a["plot"]) if a.get("plot") in plot_options else 0)
                chart = p2.radio("차트 종류", ["막대", "꺾은선", "표만"], horizontal=True, key=f"a{i}_chart",
                                 index=["막대", "꺾은선", "표만"].index(a.get("chart", "꺾은선" if is_time(keys[0]) else "막대")))
                a.update({"keys": keys, "values": values, "agg": agg, "ratio": ratio, "plot": plot,
                          "chart": chart, "table_csv": table.to_csv(index=False)})
                draw_chart(a)
                slot = f"2-3-{i}"
                if st.button("AI에게 해석 요청", key=f"btn_{slot}"):
                    call_ai(slot, f"""[주] 너는 데이터 분석가야.
[문] {W['ppm']['people'] or '팀장'}에게 보고할 '{W['task']}'를 준비하고 있어. 보고 목적은 '{W['ppm']['purpose']}'이야.
[제] 파이썬이 계산한 집계표({agg}, 기준: {', '.join(keys)})
{table.to_csv(index=False)}
[작] 하위 질문 '{W['subs'][i]['q']}'에 답하는 발견을 숫자와 함께 3줄로 정리해 줘.
- 표에 있는 숫자만 쓰고, 새로 계산했다면 계산식을 함께 적어.
- 시간의 차이(이전 대비)나 집단의 차이(그룹 간)를 짚어 줘.
- 이 표만으로 단정할 수 없는 점이 있으면 한 줄로 밝혀 줘.""")
                show_ai(slot, "AI의 해석 (표의 숫자와 맞는지 꼭 확인하세요)")
                a.setdefault("finding", "")
                a.setdefault("headline", "")
                field("내가 고른 발견 한 줄 (내 말로)", f"analyses.{i}.finding",
                      placeholder="예) 12월 이탈이 120명으로 전월(500명)보다 크게 줄었다")
                field("이 차트의 헤드라인 (결론형 한 문장)", f"analyses.{i}.headline",
                      placeholder="예) 이탈이 줄어 고객 180명 순증, 이탈 방지에 집중해야")
                st.session_state.setdefault(f"a{i}_use", a.get("use", True))
                a["use"] = st.checkbox("인사이트 보드에 넣기", key=f"a{i}_use")
    step_footer(step)

elif step == "2-4":
    ready = [a for a in W["analyses"] if a.get("table_csv")]
    need(ready, "2-3에서 분석을 하나 이상 해 주세요.")
    gaps = ["시간의 차이", "집단의 차이", "목표의 차이"]
    st.session_state.setdefault("f_gap_type", W["gap_type"] if W["gap_type"] in gaps else gaps[1])
    W["gap_type"] = st.radio("어떤 차이(Gap)를 찾았나요?", gaps, horizontal=True, key="f_gap_type",
                             help="시간: 과거보다 왜 변했나 / 집단: 왜 이 그룹만 심각한가 / 목표: 기준선과 얼마나 먼가")
    field("문제 정의 (차이 + 해석 + 해결 방향을 한 문장으로)", "problem", area=True, height=90,
          placeholder="Bad) 30대 이탈이 많다 → Good) 30대 이탈이 다른 연령대보다 높아 신규를 늘려도 고객이 줄어드는 구조이므로, 30대 이탈 방지가 먼저다")
    findings = "\n".join(f"- {W['subs'][i]['q']}: {a.get('finding', '')}" for i, a in enumerate(W["analyses"]) if a.get("table_csv"))
    ai_button("‘So What?’ 점검받기", "2-4", lambda: f"""[핵심 질문] {W['core_q']}
[PPM 메시지(가설)] {W['ppm']['message']}
[분석에서 고른 발견]
{findings}
[차이 유형] {W['gap_type']}
[교육생의 문제 정의] {W['problem']}

[요청]
1. 좋은 문제 정의 체크리스트 3가지로 판정해 줘: 기준 대비 '차이'를 강조했는가 / 'So What?'에 답할 해석이 있는가 / 해결 방향이 그려지는가.
2. 상사가 'So What?'이라고 물을 때 교육생이 더 생각해 볼 꼬리 질문 2개를 던져 줘.
3. 분석 결과로 볼 때 처음의 메시지(가설)가 맞았는지, 고쳐야 하는지 한 줄로 말해 줘.""")
    prefill("final_message", W["ppm"]["message"])
    field("최종 핵심 메시지 (분석 결과로 증명된 결론)", "final_message", area=True, height=80)
    st.subheader("나의 인사이트 보드")
    p = W["ppm"]
    st.markdown(f"**① 보고서 뼈대** · 목적: {p['purpose']} · 청중: {p['people']}")
    shown = [(i, a) for i, a in enumerate(W["analyses"]) if a.get("table_csv") and a.get("use", True)]
    cols = st.columns(max(1, min(3, len(shown))))
    for (i, a), col in zip(shown, cols):
        with col:
            st.markdown(f"**{a.get('headline') or W['subs'][i]['q']}**")
            draw_chart(a)
    st.markdown(f"**③ 핵심 메시지** · {W['final_message'] or p['message']}")
    st.download_button("인사이트 보드 내려받기 (.md)", board_md(), file_name="인사이트보드.md", mime="text/markdown")
    step_footer(step)

# ---------------------------------------------------------
# 모듈 3
# ---------------------------------------------------------
elif step == "3-1":
    prefill("scqa.A", W["final_message"] or W["ppm"]["message"])
    st.caption("A(해답)에는 2-4의 최종 핵심 메시지가 들어 있습니다. S·C·Q를 채워 A에 도달하는 길을 만드세요.")
    field("S 상황 — 현재 상황은 어떠한가?", "scqa.S", area=True, height=80)
    field("C 한계 — 기존 방식은 왜 통하지 않나?", "scqa.C", area=True, height=80)
    field("Q 핵심 질문 — 우리가 풀어야 할 것은?", "scqa.Q", area=True, height=80)
    field("A 해답 — 어떻게 해결할 것인가?", "scqa.A", area=True, height=80)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("막힐 때: S·C·Q 초안 제안받기", key="btn_3-1a"):
            call_ai("3-1a", f"""{board_md()}

[요청] 이 인사이트 보드의 핵심 메시지가 SCQA의 A(해답)야.
A에 자연스럽게 도달하도록 S(상황), C(기존 방식의 한계), Q(핵심 질문)의 '초안 제안'을 한 줄씩 써 줘.
보드에 없는 숫자는 쓰지 마. 교육생이 고쳐 쓸 수 있게 짧게.""")
    with c2:
        if st.button("SCQA 논리 점검받기", key="btn_3-1b"):
            call_ai("3-1b", f"""[교육생의 SCQA]
S: {W['scqa']['S']}
C: {W['scqa']['C']}
Q: {W['scqa']['Q']}
A: {W['scqa']['A']}
[청중] {W['ppm']['people']}

[요청] S → C → Q → A가 끊기지 않고 이어지는지 점검해 줘.
연결이 약한 곳 한 군데와, 청중이 A를 읽고 '왜?'라고 물을 지점을 알려 줘. 답을 대신 써 주지는 마.""")
    show_ai("3-1a", "AI의 초안 제안 (그대로 쓰지 말고 내 말로 고치세요)")
    show_ai("3-1b")
    step_footer(step)

elif step == "3-2":
    st.caption("보고서에 들어갈 주장과 숫자를 한 줄씩 적습니다. 원본에서 확인한 숫자만 ‘원본 대조’로 바꾸세요.")
    if st.button("인사이트 보드의 발견을 표로 가져오기", key="btn_import_facts"):
        existing = {f["주장"] for f in W["facts"]}
        for i, a in enumerate(W["analyses"]):
            if a.get("table_csv") and a.get("finding") and a["finding"] not in existing:
                W["facts"].append({"주장": a["finding"], "숫자": "", "출처": W["data_name"], "확인": "확인 필요"})
        st.session_state.pop("f_facts_editor", None)
    # 편집기의 기준 표는 처음 그릴 때(또는 가져오기 직후)에만 새로 만듭니다. 편집 내용은 편집기가 기억합니다.
    if "f_facts_editor" not in st.session_state or "facts_base" not in st.session_state:
        st.session_state.facts_base = pd.DataFrame(
            W["facts"] or [{"주장": "", "숫자": "", "출처": "", "확인": "확인 필요"}],
            columns=["주장", "숫자", "출처", "확인"])
    edited = st.data_editor(
        st.session_state.facts_base, num_rows="dynamic", hide_index=True, key="f_facts_editor", width="stretch",
        column_config={
            "주장": st.column_config.TextColumn("주장", width="large"),
            "숫자": st.column_config.TextColumn("숫자"),
            "출처": st.column_config.TextColumn("출처 (파일명·기관·링크)"),
            "확인": st.column_config.SelectboxColumn("확인", options=CHECK_STATUS, required=True),
        })
    W["facts"] = [r for r in edited.fillna("").to_dict("records") if str(r["주장"]).strip()]
    pending = sum(1 for f in W["facts"] if f["확인"] == "확인 필요")
    if pending:
        st.warning(f"‘확인 필요’가 {pending}건 남아 있습니다. 확인하지 못한 숫자는 보고서에 쓰지 않습니다.")
    elif W["facts"]:
        st.success("모든 주장의 확인을 마쳤습니다.")
    ai_button("보강할 근거 아이디어 받기", "3-2", lambda: f"""[핵심 메시지] {W['final_message'] or W['ppm']['message']}
[SCQA]
S: {W['scqa']['S']}
C: {W['scqa']['C']}
[팩트체크 표]
{facts_md()}

[요청]
1. 이 보고서의 논리에서 근거가 약한 곳 2군데를 짚어 줘.
2. 그 빈틈을 채울 외부 자료를 찾을 '검색 키워드'를 기관명·조사명·지표명 형태로 제안해 줘.
3. 구체적인 보고서 제목이나 숫자는 지어내지 마. 실제로 있는지는 교육생이 직접 검색해 확인해야 한다고 알려 줘.""")
    step_footer(step)

elif step == "3-3":
    with st.expander("마스터 소스 보기 (질문 카드 + 인사이트 보드 + SCQA + 팩트체크 표)"):
        st.markdown(master_source())
    c1, c2 = st.columns(2)
    length = c1.radio("분량", ["A4 1쪽", "A4 2쪽"], horizontal=True, key="d_length")
    style = c2.radio("문체", ["개조식", "서술식"], horizontal=True, key="d_style")
    if st.button("AI에게 초안 쓰기 요청", type="primary", key="btn_3-3"):
        result = call_ai("3-3", f"""[주] 너는 전략기획팀의 보고서 작성 전문가야.
[문] {W['ppm']['people'] or '팀장'}에게 '{W['task']}'를 보고해 승인을 받으려 해. 목적은 '{W['ppm']['purpose']}'이야.
[제] 아래 마스터 소스
{master_source()}
[작] {length} 분량의 {style} 보고서 초안을 마크다운으로 써 줘.
- 순서: 결론이 담긴 한 문장 제목 → 3줄 요약 → 상황 → 한계 → 핵심 질문 → 해답 → 기대효과
- 숫자는 원문 그대로 쓰고, 출처를 괄호로 달아.
- 팩트체크 표에서 '확인 필요'인 숫자는 쓰지 마.""", system=WRITER)
        if result:
            W["draft"] = result
            st.session_state["f_draft"] = result
    if W["prompts"].get("3-3"):
        with st.expander("AI에게 실제로 보낸 프롬프트 보기"):
            st.code(W["prompts"]["3-3"], language=None)
    field("보고서 초안 (직접 고칠 수 있습니다)", "draft", area=True, height=420,
          help="내가 설명할 수 없는 문장은 고치거나 지우세요.")
    if W["draft"]:
        with st.expander("미리보기", expanded=True):
            st.markdown(W["draft"])
    step_footer(step)

elif step == "3-4":
    if need(W["draft"].strip(), "먼저 3-3에서 초안을 만들어 주세요."):
        st.subheader("① 퇴고")
        if st.button("결론형 제목 · 3줄 요약으로 퇴고하기", key="btn_3-4a"):
            result = call_ai("3-4a", f"""[보고서 초안]
{W['draft']}

[요청]
1. 각 단락 제목을 결론이 담긴 한 문장으로 바꾸고, 제목만 이어 읽어도 이야기가 되게 해 줘.
2. 맨 위 3줄 요약을 다듬어 줘.
3. 숫자와 출처는 절대 바꾸지 마. 보고서 전체를 마크다운으로 돌려줘.""", system=WRITER)
            if result:
                W["revised"] = result
        if W["revised"]:
            with st.container(border=True):
                st.markdown(W["revised"])

            def adopt():
                W["draft"] = W["revised"]
                st.session_state["f_draft"] = W["revised"]
            st.button("퇴고본을 내 보고서로 쓰기", on_click=adopt, key="btn_adopt")

        st.subheader("② 마지막 환각 검사")
        tables = "\n\n".join(f"[분석표 {'①②③'[i]}]\n{a['table_csv']}" for i, a in enumerate(W["analyses"]) if a.get("table_csv"))
        ai_button("보고서와 근거 자료 대조하기", "3-4b", lambda: f"""[보고서]
{W['draft']}

[팩트체크 표]
{facts_md()}

{tables}

[요청] 보고서의 숫자와 주장을 팩트체크 표와 분석표에 대조해 줘.
형식: 보고서 문장 | 근거 자료의 값 | 판정(일치 / 불일치 / 근거 없음) 의 표.
일치하는 것은 생략하지 말고 모두 적어. 마지막에 고쳐야 할 문장 목록만 따로 정리해 줘.""", title="환각 검사 결과")

        st.subheader("③ 깐깐한 상사의 예상 질문")
        prefill("persona.title", W["ppm"]["people"])
        c1, c2, c3 = st.columns(3)
        with c1:
            field("직책", "persona.title")
        with c2:
            field("판단 기준", "persona.criteria", placeholder="예) 숫자로 증명되는가, 실행 가능한가")
        with c3:
            field("단골 질문 · 싫어하는 표현", "persona.questions", placeholder="예) 출처가 어디야? / '차후 검토'")
        ai_button("예상 질문 5개 받기", "3-4c", lambda: f"""[페르소나] 너는 {W['persona']['title'] or '팀장'}이야. 판단 기준은 '{W['persona']['criteria']}', 단골 질문과 싫어하는 표현은 '{W['persona']['questions']}'이야.
[보고서]
{W['draft']}

[요청] 이 보고서를 보고받는다면 꼭 나올 질문 3개와 가장 답하기 어려운 질문 2개를 뽑아 줘.
질문마다 보고서에서 답의 근거가 되는 부분이 있는지(있음/없음)도 표시해 줘.""", system=COACH, title="예상 질문")

        st.subheader("④ 완성 체크")
        items = {
            "titles": "제목만 읽어도 결론이 보인다",
            "sources": "모든 숫자에 출처가 붙어 있다",
            "nopending": "팩트체크 표에 ‘확인 필요’가 남지 않았다",
            "qa": "예상 질문에 답할 수 있다",
        }
        for k, label in items.items():
            st.session_state.setdefault(f"chk_{k}", W["checks"].get(k, False))
            W["checks"][k] = st.checkbox(label, key=f"chk_{k}")
        pending = sum(1 for f in W["facts"] if f["확인"] == "확인 필요")
        if pending:
            st.caption(f"참고: 팩트체크 표에 ‘확인 필요’가 {pending}건 있습니다.")
        if all(W["checks"].get(k) for k in items):
            st.success("완성! 모듈 4에서 이 과정을 반복해 주는 나만의 에이전트를 만듭니다.")

        package = "\n\n---\n\n".join([
            card_md(), board_md(), "# 한 장 보고서\n\n" + W["draft"], "# 팩트체크 표\n\n" + facts_md(),
        ])
        st.download_button("최종 패키지 내려받기 (질문 카드 + 인사이트 보드 + 보고서 + 팩트체크 표)",
                           package, file_name=f"실전보고서_{W['name'] or '교육생'}.md", mime="text/markdown",
                           type="primary")
    step_footer(step)
