"""
AI 운동재활 시스템 v3.0
- 빈칸 제거, 라이트 모드
- 검사 방법 초상세 텍스트
- 운동 카드 (이모지 그림 + 목적 + 상세 방법)
- 6개월 주기화 프로그램 (주차별 클릭)
- 운동 기록 (세트/특이사항/운동 추가)
- Haiku 모델로 빠른 응답
"""

import streamlit as st
import anthropic
import re
import csv
import io
import json
from datetime import datetime

st.set_page_config(page_title="AI 운동재활 시스템", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
html,body,[class*="css"]{font-family:'Noto Sans KR',sans-serif;color:#1a1a2e;}
.stApp{background:#f5f7fa;}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e0e4ea;}
.card{background:#fff;border:1px solid #e0e4ea;border-radius:12px;padding:18px 22px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,0.05);}
.card-blue{border-left:4px solid #2563eb;}
.card-green{border-left:4px solid #16a34a;}
.card-red{border-left:4px solid #dc2626;}
.card-purple{border-left:4px solid #7c3aed;}
.card-orange{border-left:4px solid #ea580c;}
.ex-card{background:#fff;border:1px solid #e0e4ea;border-radius:12px;padding:16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);}
.ex-icon{font-size:2.5rem;text-align:center;margin-bottom:6px;}
.ex-name{font-weight:700;font-size:1rem;color:#1e3a8a;margin-bottom:4px;}
.ex-goal{font-size:0.78rem;color:#6b7280;margin-bottom:6px;}
.ex-method{font-size:0.82rem;color:#374151;background:#f0f4ff;border-radius:8px;padding:8px 10px;}
.metric{background:#f0f4ff;border-radius:10px;padding:12px 16px;text-align:center;}
.metric-label{color:#6b7280;font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;}
.metric-value{color:#2563eb;font-size:1.4rem;font-weight:700;}
.week-header{background:linear-gradient(135deg,#2563eb,#1d4ed8);color:white;border-radius:10px;padding:12px 18px;font-weight:700;margin-bottom:12px;}
.record-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin-top:6px;}
.pos{background:#fee2e2;color:#b91c1c;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;}
.neg{background:#dcfce7;color:#15803d;border-radius:6px;padding:2px 10px;font-size:0.75rem;font-weight:700;}
.app-title{font-size:1.7rem;font-weight:700;color:#1e3a8a;}
.app-sub{font-size:0.83rem;color:#6b7280;}
.stButton>button{background:linear-gradient(135deg,#2563eb,#1d4ed8)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:600!important;padding:10px 24px!important;}
[data-testid="stTabs"] [data-baseweb="tab"]{color:#6b7280!important;font-weight:500;}
[data-testid="stTabs"] [aria-selected="true"]{color:#2563eb!important;border-bottom-color:#2563eb!important;}
[data-testid="stExpander"]{background:#fff;border:1px solid #e0e4ea;border-radius:10px;}
hr{border-color:#e0e4ea;}
</style>
""", unsafe_allow_html=True)

# ── API KEY ───────────────────────────────────────────────────────────────────
try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_API_KEY = ""  # 🔑 여기에 API 키 입력

# ── 운동 아이콘 매핑 ───────────────────────────────────────────────────────────
EXERCISE_ICONS = {
    "스트레칭": "🧘", "stretch": "🧘", "flexibility": "🧘",
    "플랭크": "💪", "코어": "💪", "안정화": "💪",
    "스쿼트": "🦵", "런지": "🦵", "하체": "🦵",
    "푸시업": "🏋️", "벤치": "🏋️", "상체": "🏋️",
    "걷기": "🚶", "보행": "🚶", "walking": "🚶",
    "밴드": "🎯", "저항": "🎯", "resistance": "🎯",
    "균형": "⚖️", "balance": "⚖️", "proprioception": "⚖️",
    "수영": "🏊", "수중": "🏊",
    "자전거": "🚴", "사이클": "🚴",
    "호흡": "🌬️", "breathing": "🌬️",
    "마사지": "👐", "foam": "👐", "롤러": "👐",
    "default": "🏃"
}

def get_exercise_icon(name):
    name_lower = name.lower()
    for key, icon in EXERCISE_ICONS.items():
        if key in name_lower:
            return icon
    return EXERCISE_ICONS["default"]

# ── 상세 검사 DB ──────────────────────────────────────────────────────────────
TEST_DB = {
    "경추 (Cervical)": [
        {"id":"C1","name":"Spurling Test","goal":"신경근 압박 확인","method":"""
**준비 자세:** 환자는 의자에 바르게 앉습니다. 검사자는 환자 뒤에 섭니다.

**검사 순서:**
1. 환자의 고개를 검사할 방향(아픈 쪽)으로 약 30° 측굴시킵니다
2. 동시에 고개를 같은 방향으로 약 20° 회전시킵니다
3. 검사자는 양손을 환자의 두정부(머리 위)에 올립니다
4. 아래 방향으로 서서히 약 7~10kg 압력을 가합니다
5. 환자에게 팔이나 어깨로 뻗치는 통증/저림이 있는지 확인합니다

**양성 판정:** 팔, 어깨, 손으로 방사되는 통증이나 저림이 재현되면 양성
**주의:** 급격한 압박 금지, 환자가 불편함 호소 시 즉시 중단""","video":"https://www.youtube.com/results?search_query=Spurling+test+demonstration"},
        {"id":"C2","name":"Distraction Test","goal":"신경근 압박 경감 확인","method":"""
**준비 자세:** 환자는 의자에 앉습니다. 검사자는 환자 정면에 섭니다.

**검사 순서:**
1. 검사자는 한 손을 환자의 턱 아래, 다른 손을 후두부(뒤통수)에 댑니다
2. 서서히 수직 방향으로 두부를 위로 견인합니다 (약 10~15kg)
3. 10~15초 유지합니다
4. 증상이 감소하거나 소실되는지 확인합니다

**양성 판정:** 견인 시 방사통/저림이 감소 또는 소실되면 양성 (신경근 압박 의심)
**의미:** 양성이면 Spurling 양성과 함께 경추 신경근증 가능성 높음""","video":"https://www.youtube.com/results?search_query=cervical+distraction+test"},
        {"id":"C3","name":"ULTT1 (정중신경)","goal":"정중신경 긴장 확인","method":"""
**준비 자세:** 환자는 검사대에 반듯이 눕습니다.

**검사 순서:**
1. 검사자는 견갑대를 아래로 눌러 고정합니다
2. 어깨를 110° 외전시킵니다
3. 팔꿈치를 신전(펼침) 시킵니다
4. 전완을 회외(손바닥 위) 시킵니다
5. 손목을 신전시킵니다
6. 고개를 반대편으로 측굴하여 증상 변화 확인합니다

**양성 판정:** 검사 측 팔에 저림, 통증, 감각 이상이 나타나면 양성
**주의:** 각 단계를 천천히 진행, 증상 즉시 확인""","video":"https://www.youtube.com/results?search_query=upper+limb+tension+test+ULTT"},
        {"id":"C4","name":"Sharp-Purser Test","goal":"환추-축추 불안정성","method":"""
**준비 자세:** 환자는 의자에 앉아 고개를 앞으로 굴곡시킵니다.

**검사 순서:**
1. 한 손 검지를 축추(C2) 극돌기에 대고 고정합니다
2. 다른 손 손바닥을 환자의 이마에 댑니다
3. 이마를 뒤쪽(후방)으로 부드럽게 밀면서 경추를 후방 전위시킵니다
4. '뚝' 소리나 느낌, 또는 증상 감소 여부를 확인합니다

**양성 판정:** 후방 압박 시 두통/어지럼 감소, 또는 '뚝' 느낌이 나면 양성
**⚠️ 주의:** 류마티스 관절염 환자에게 특히 중요, 매우 부드럽게 시행""","video":"https://www.youtube.com/results?search_query=Sharp+Purser+test"},
    ],
    "견관절 (Shoulder)": [
        {"id":"S1","name":"Neer Impingement Sign","goal":"충돌증후군 확인","method":"""
**준비 자세:** 환자는 서거나 앉습니다. 검사자는 환자 옆에 섭니다.

**검사 순서:**
1. 한 손으로 환자의 견갑골을 뒤에서 고정합니다 (회전 방지)
2. 환자의 팔을 완전 내회전시킵니다 (엄지가 아래를 향하게)
3. 팔꿈치를 편 상태로 팔을 앞쪽(전방 굴곡) 방향으로 서서히 올립니다
4. 60~120° 구간에서 통증 발생 여부를 확인합니다

**양성 판정:** 어깨 전상방에 통증이 발생하면 양성
**임상 의미:** 극상근 또는 견봉하 점액낭 충돌 의심""","video":"https://www.youtube.com/results?search_query=Neer+impingement+test+shoulder"},
        {"id":"S2","name":"Hawkins-Kennedy Test","goal":"충돌증후군 확인","method":"""
**준비 자세:** 환자는 서거나 앉습니다.

**검사 순서:**
1. 환자의 어깨를 90° 전방 굴곡시킵니다 (팔이 앞으로 수평)
2. 팔꿈치를 90° 굴곡시킵니다
3. 검사자는 전완을 잡고 내회전(손이 아래로 내려가도록) 강요합니다
4. 어깨 전방부의 통증 발생 여부를 확인합니다

**양성 판정:** 내회전 시 어깨 전상방 통증이 유발되면 양성
**임상 의미:** Neer 검사보다 민감도 높음, 극상건 충돌 시사""","video":"https://www.youtube.com/results?search_query=Hawkins+Kennedy+test"},
        {"id":"S3","name":"Empty Can Test","goal":"극상근 파열/약화","method":"""
**준비 자세:** 환자는 서거나 앉습니다.

**검사 순서:**
1. 어깨를 견갑면(전방 30°)으로 90° 외전시킵니다
2. 팔을 완전 내회전시킵니다 (엄지가 바닥을 향함, 캔 비우는 자세)
3. 검사자는 팔꿈치 위 전완 부위에 아래쪽 저항을 가합니다
4. 환자는 저항에 맞서 팔을 올린 자세를 유지합니다
5. 통증이나 근력 약화 여부를 건측과 비교합니다

**양성 판정:** 통증 발생 또는 저항 유지 불가 시 양성
**임상 의미:** 극상근 파열 또는 신경 손상 의심""","video":"https://www.youtube.com/results?search_query=empty+can+test+supraspinatus"},
        {"id":"S4","name":"Apprehension Test","goal":"전방 불안정성 확인","method":"""
**준비 자세:** 환자는 검사대에 눕거나 앉습니다.

**검사 순서:**
1. 어깨를 90° 외전시킵니다
2. 팔꿈치를 90° 굴곡시킵니다
3. 서서히 최대 외회전으로 유도합니다
4. 환자의 표정과 불안감(어깨가 빠질 것 같은 느낌) 확인합니다
5. Relocation: 이 자세에서 상완골두를 후방으로 압박하면 불안감 소실

**양성 판정:** 외회전 시 어깨가 빠질 것 같은 불안감 호소 시 양성
**임상 의미:** 전방 관절낭/관절와순 손상 의심 (뱅카트 병변)""","video":"https://www.youtube.com/results?search_query=shoulder+apprehension+test+anterior+instability"},
        {"id":"S5","name":"O'Brien Test","goal":"SLAP 병변/AC관절","method":"""
**준비 자세:** 환자는 서거나 앉습니다.

**검사 순서:**
1. 어깨를 90° 굴곡, 팔꿈치 완전 신전시킵니다
2. 수평 내전 약 15° 유지합니다
3. **1단계:** 완전 내회전(엄지 아래) 상태에서 위에서 아래로 저항
4. **2단계:** 완전 외회전(손바닥 위) 상태에서 동일한 저항
5. 두 단계에서 통증 위치와 강도를 비교합니다

**양성 판정:** 내회전 시 통증 > 외회전 시 통증 = SLAP 양성
**통증 위치:** 어깨 위쪽 → SLAP / 어깨 앞쪽 → AC관절 문제""","video":"https://www.youtube.com/results?search_query=OBrien+active+compression+test+SLAP"},
    ],
    "주관절 (Elbow)": [
        {"id":"E1","name":"Cozen's Test","goal":"외측 상과염 확인","method":"""
**준비 자세:** 환자는 팔꿈치를 90° 굴곡하고 앉습니다.

**검사 순서:**
1. 검사자는 환자의 팔꿈치 외측 상과 부위를 한 손으로 촉진·고정합니다
2. 환자에게 손목을 신전(뒤로 젖히기)하고 주먹을 쥐도록 합니다
3. 검사자는 환자의 손등에 손목 굴곡 방향으로 저항을 가합니다
4. 외측 상과 부위의 통증 발생을 확인합니다

**양성 판정:** 외측 상과 부위에 날카로운 통증이 발생하면 양성
**임상 의미:** 테니스 엘보 (단요측수근신근 기시부 병변)""","video":"https://www.youtube.com/results?search_query=Cozen+test+tennis+elbow"},
        {"id":"E2","name":"Golfer's Elbow Test","goal":"내측 상과염 확인","method":"""
**준비 자세:** 환자는 팔꿈치를 약간 굴곡하고 앉습니다.

**검사 순서:**
1. 검사자는 내측 상과를 엄지로 직접 압박합니다
2. 환자의 전완을 회외(손바닥 위쪽)시킵니다
3. 손목을 신전(뒤로 젖히기)시킵니다
4. 팔꿈치를 서서히 신전시킵니다
5. 내측 상과 부위 통증 재현 확인합니다

**양성 판정:** 내측 상과에 통증이 재현되면 양성
**임상 의미:** 골퍼 엘보 (원형회내근/요측수근굴근 기시부 병변)""","video":"https://www.youtube.com/results?search_query=golfer+elbow+test+medial+epicondylitis"},
    ],
    "요추 (Lumbar)": [
        {"id":"L1","name":"Straight Leg Raise (SLR)","goal":"좌골신경 긴장/추간판 탈출","method":"""
**준비 자세:** 환자는 검사대에 반듯이 눕습니다(앙와위). 두 다리를 펴고 편안히 눕습니다.

**검사 순서:**
1. 검사자는 한 손을 환자의 발뒤꿈치 아래에 놓습니다
2. 다른 손으로 무릎이 구부러지지 않도록 슬와부(무릎 뒤)를 가볍게 누릅니다
3. 무릎을 완전히 편 상태로 다리를 서서히 올립니다
4. 통증이 발생하는 각도를 기록합니다 (정상: 80°이상)
5. 통증 발생 시 발목을 배측굴곡(발등 들기)하여 증상 악화 확인 (Bragard Test)

**양성 판정:** 30~70° 사이에서 허리/엉덩이/다리로 방사되는 통증 발생 시 양성
**⚠️ 주의:** 단순 뒤쪽 허벅지 당김은 양성이 아님, 반드시 방사통이어야 함""","video":"https://www.youtube.com/results?search_query=straight+leg+raise+test+sciatic"},
        {"id":"L2","name":"Slump Test","goal":"신경 조직 긴장 확인","method":"""
**준비 자세:** 환자는 검사대 끝에 앉아 손을 등 뒤로 모읍니다.

**검사 순서:**
1. 환자에게 몸통을 앞으로 구부리도록(흉요추 굴곡) 합니다
2. 고개를 앞으로 굴곡(턱을 가슴에 대듯)시킵니다
3. 검사자는 한 손으로 두부를 굴곡 고정합니다
4. 검사 측 무릎을 완전히 펩니다
5. 발목을 배측굴곡(발등 들기)합니다
6. 고개를 신전시켜 증상이 감소하면 양성 확인

**양성 판정:** 신경 경로를 따라 통증/저림 발생, 고개 신전 시 증상 감소 시 양성
**임상 의미:** SLR보다 민감도 높음, 신경 유착이나 긴장 의심""","video":"https://www.youtube.com/results?search_query=slump+test+neural+tension"},
        {"id":"L3","name":"FABER Test","goal":"SI관절/고관절 병변","method":"""
**준비 자세:** 환자는 검사대에 반듯이 눕습니다.

**검사 순서:**
1. 검사 측 발을 반대편 무릎 위에 올립니다 (4자 모양)
2. 검사 측 고관절이 굴곡-외전-외회전 자세가 됩니다
3. 한 손은 반대편 ASIS(전상장골극)를 고정합니다
4. 다른 손으로 검사 측 무릎을 바닥 방향으로 서서히 압박합니다
5. 통증 위치(서혜부, SI관절, 고관절)를 확인합니다

**양성 판정:** 검사 측 SI관절 또는 서혜부/고관절에 통증 발생 시 양성
**통증 위치에 따른 감별:** 서혜부→고관절 병변 / 후방→SI관절 병변""","video":"https://www.youtube.com/results?search_query=FABER+Patrick+test+hip"},
    ],
    "슬관절 (Knee)": [
        {"id":"K1","name":"Lachman Test","goal":"ACL 손상 확인","method":"""
**준비 자세:** 환자는 검사대에 반듯이 눕습니다. 무릎을 20~30° 굴곡시킵니다.

**검사 순서:**
1. 한 손으로 대퇴골 원위부(무릎 위 허벅지)를 단단히 고정합니다
2. 다른 손으로 경골 근위부(무릎 아래)를 감싸 쥡니다
3. 경골을 전방(앞쪽)으로 빠르게 당깁니다
4. 대퇴골 대비 경골의 전방 이동량과 단단한 끝느낌(end feel)을 평가합니다
5. 반대편과 비교합니다

**양성 판정:** 경골이 5mm 이상 전방 전위되거나 end feel이 물렁하면 양성
**등급:** 1도(3~5mm) / 2도(6~10mm) / 3도(10mm 초과)
**임상 의미:** ACL 전방십자인대 손상""","video":"https://www.youtube.com/results?search_query=Lachman+test+ACL+knee"},
        {"id":"K2","name":"McMurray Test","goal":"반월연골판 손상","method":"""
**준비 자세:** 환자는 검사대에 반듯이 눕습니다.

**검사 순서:**
1. 무릎을 최대한 굴곡시킵니다
2. **내측 반월판 검사:** 발을 외회전시키고 무릎에 외반 스트레스를 주면서 서서히 신전
3. **외측 반월판 검사:** 발을 내회전시키고 무릎에 내반 스트레스를 주면서 서서히 신전
4. 각 동작에서 '클릭'소리, 잠김(locking), 통증 발생 확인합니다

**양성 판정:** 신전 과정에서 관절선 부위에 통증 또는 클릭이 발생하면 양성
**주의:** 급성 손상 시 최대 굴곡 주의, 천천히 시행""","video":"https://www.youtube.com/results?search_query=McMurray+test+meniscus+knee"},
    ],
    "족관절 (Ankle/Foot)": [
        {"id":"A1","name":"Anterior Drawer (Ankle)","goal":"ATFL 손상 확인","method":"""
**준비 자세:** 환자는 검사대에 앉거나 눕습니다. 발목을 약 20° 족저굴곡(발끝 내리기)시킵니다.

**검사 순서:**
1. 한 손으로 하퇴 원위부(발목 위 정강이)를 단단히 고정합니다
2. 다른 손으로 발뒤꿈치를 감싸 쥡니다
3. 발뒤꿈치를 전방(앞쪽)으로 당깁니다
4. 거골의 전방 이동량을 평가하고 반대편과 비교합니다

**양성 판정:** 3~5mm 이상 전방 전위 또는 딤플(피부 함몰) 발생 시 양성
**임상 의미:** ATFL(전거비인대) 손상, 발목 염좌 가장 흔한 손상 부위""","video":"https://www.youtube.com/results?search_query=anterior+drawer+test+ankle+ATFL"},
        {"id":"A2","name":"Thompson Test","goal":"아킬레스건 파열 확인","method":"""
**준비 자세:** 환자는 복와위(엎드려)로 눕고 발을 검사대 끝 밖으로 내놓습니다.

**검사 순서:**
1. 종아리 근육(비복근)의 중간 부위를 손으로 쥡니다
2. 근육을 부드럽게 짜듯이 압박합니다
3. 발목의 족저굴곡(발끝이 아래로) 반응을 관찰합니다
4. 반대편과 비교합니다

**양성 판정:** 종아리를 쥐었을 때 발끝이 움직이지 않으면 양성 (파열 의심)
**⚠️ 임상 의미:** 아킬레스건 완전 파열 — 즉시 정형외과 의뢰 필요""","video":"https://www.youtube.com/results?search_query=Thompson+test+achilles+tendon+rupture"},
    ],
    "뇌신경 (Neurological)": [
        {"id":"N1","name":"Romberg Test","goal":"고유수용감각/소뇌 기능","method":"""
**준비 자세:** 환자는 평평한 바닥에 맨발로 섭니다. 안전을 위해 검사자가 옆에 서 있습니다.

**검사 순서:**
1. 발을 모으고(발뒤꿈치와 발끝 붙이기) 바르게 섭니다
2. **눈 뜬 상태** 30초 균형 유지 (정상 확인)
3. **눈 감은 상태** 30초 균형 유지 관찰
4. 흔들림, 발 이동, 낙상 경향을 관찰합니다

**양성 판정:** 눈 감았을 때 현저한 흔들림 또는 낙상 경향 시 양성
**감별:** 눈 뜰 때도 불안정 → 소뇌 문제 / 눈 감을 때만 불안정 → 고유수용감각 문제""","video":"https://www.youtube.com/results?search_query=Romberg+test+balance+assessment"},
        {"id":"N2","name":"Timed Up and Go (TUG)","goal":"기능적 이동성 확인","method":"""
**준비 자세:** 팔걸이 있는 의자, 3m 전방에 테이프 표시. 환자는 의자에 등받이에 기대어 앉습니다.

**검사 순서:**
1. 시작 신호와 함께 타이머 시작
2. 환자가 의자에서 일어섭니다
3. 3m를 걸어갑니다
4. 돌아서서 다시 3m를 걸어옵니다
5. 의자에 앉을 때 타이머 정지

**정상 기준:**
- 10초 이하: 정상 이동성
- 10~20초: 경계 (낙상 위험 중등도)
- 20초 이상: 낙상 위험 높음

**기록:** 초(sec) 단위로 기록, 3회 시행 평균""","video":"https://www.youtube.com/results?search_query=timed+up+and+go+TUG+test"},
        {"id":"N3","name":"Dix-Hallpike Test","goal":"BPPV(이석증) 확인","method":"""
**준비 자세:** 환자는 검사대에 앉습니다. 검사대가 충분히 길어야 합니다.

**검사 순서:**
1. 환자에게 눈을 뜨고 있도록 합니다
2. 고개를 검사 측으로 45° 회전시킵니다
3. 검사자는 환자 양쪽 어깨를 잡고 빠르게 뒤로 눕힙니다
4. 머리가 검사대 끝 밖으로 30° 신전되도록 합니다
5. 30초간 안진(눈 떨림)과 어지럼 발생 관찰합니다

**양성 판정:** 5~40초 후 회전성 안진 및 어지럼 발생 시 양성
**⚠️ 주의:** 경추 불안정성 환자 주의, 구역질 대비, 빠르게 시행해야 정확""","video":"https://www.youtube.com/results?search_query=Dix+Hallpike+test+BPPV"},
    ],
    "다이어트 / 체력검사": [
        {"id":"D1","name":"심폐지구력 (3분 스텝 검사)","goal":"유산소 능력 평가","method":"""
**준비물:** 30cm 높이 스텝(계단), 메트로놈(분당 96박자), 타이머

**검사 순서:**
1. 메트로놈을 96bpm으로 설정합니다 (4박자에 1사이클)
2. 박자에 맞춰 스텝을 오르내립니다: 올라가기(L→R) / 내려오기(L→R)
3. 3분간 쉬지 않고 지속합니다
4. 완료 즉시 앉아서 1분간 안정합니다
5. 회복 후 1분 심박수를 측정합니다 (손목 또는 목)

**평가 기준 (성인 남성 기준):**
- 우수: 70 이하 / 양호: 71~90 / 보통: 91~110 / 미흡: 111 이상""","video":"https://www.youtube.com/results?search_query=3+minute+step+test+cardiorespiratory"},
        {"id":"D2","name":"Push-Up Test","goal":"상체 근지구력","method":"""
**자세 기준 (표준):**
- 손은 어깨너비, 손가락은 앞을 향함
- 몸은 머리부터 발뒤꿈치까지 일직선
- 가슴이 바닥에서 5cm 이내로 내려오기

**여성 변형:** 무릎을 바닥에 대고 시행 가능

**검사:** 1분간 최대 횟수 측정 (중간에 쉬어도 되나 자세 유지)

**평가 (30대 남성 기준):**
- 우수: 36회 이상 / 양호: 25~35회 / 보통: 15~24회 / 미흡: 14회 이하""","video":"https://www.youtube.com/results?search_query=push+up+fitness+test"},
        {"id":"D3","name":"허리둘레 측정","goal":"복부비만 평가","method":"""
**측정 방법:**
1. 환자는 편안히 서고 숨을 자연스럽게 내쉽니다
2. 갈비뼈 최하단과 장골능(골반 위쪽) 사이 중간 지점을 찾습니다
3. 배꼽 높이에서 줄자를 피부에 밀착시켜 측정합니다
4. 숨을 내쉰 상태에서 측정합니다

**한국인 복부비만 기준:**
- 남성: 90cm 이상 = 복부비만
- 여성: 85cm 이상 = 복부비만""","video":"https://www.youtube.com/results?search_query=waist+circumference+measurement+technique"},
    ],
    "체형교정": [
        {"id":"P1","name":"Postural Assessment","goal":"전신 자세 정렬 평가","method":"""
**준비:** 격자 배경판, 카메라 또는 육안 관찰

**관찰 순서:**

**전면 관찰:**
1. 발의 외전 각도 (정상: 7~10°)
2. 무릎 내반/외반
3. 골반 높이 비교 (ASIS 높이)
4. 어깨 높이 비교
5. 두부 측방 전위

**측면 관찰:**
1. 귀-어깨-고관절-무릎-발목이 일직선인지 확인
2. 경추 전만, 흉추 후만, 요추 전만 각도
3. 골반 전/후방 경사

**후면 관찰:**
1. 척추 측만 여부
2. 견갑골 위치 (익상견갑 여부)""","video":"https://www.youtube.com/results?search_query=postural+assessment+full+body"},
        {"id":"P2","name":"Adam's Forward Bend Test","goal":"척추 측만증 선별","method":"""
**준비 자세:** 환자는 발을 모으고 바르게 섭니다.

**검사 순서:**
1. 무릎을 편 채로 허리를 앞으로 굽힙니다 (90° 전굴)
2. 손을 모아 발 방향으로 늘어뜨립니다
3. 검사자는 눈높이를 환자 등 높이에 맞춰 뒤에서 관찰합니다
4. 흉추 또는 요추 부위의 좌우 높이 차이를 관찰합니다

**양성 판정:** 한쪽이 5mm 이상 높으면 양성 (늑골 융기 = rib hump)
**측정도구:** Scoliometer 사용 시 7° 이상이면 X-ray 의뢰 권장""","video":"https://www.youtube.com/results?search_query=Adam+forward+bend+test+scoliosis+screening"},
    ],

    "흉추 (Thoracic Spine)": [
        {"id":"T1","name":"Seated Thoracic Rotation Test","goal":"흉추 회전 가동성 측정","method":"""
**준비 자세:** 환자는 팔짱을 끼고 의자에 바르게 앉습니다 (발은 고정).

**검사 순서:**
1. 골반이 움직이지 않도록 고정합니다
2. 팔짱 낀 상태로 몸통을 좌측으로 최대한 회전시킵니다
3. 각도를 측정하거나 시각적으로 평가합니다
4. 반대편도 동일하게 시행하고 좌우 비교합니다

**정상 기준:** 양측 40~50° 이상, 좌우 차이 10° 미만
**양성 판정:** 한쪽이 현저히 제한되거나 통증 발생 시
**임상 의미:** 흉추 가동성 제한 → 어깨/요추 보상 패턴 유발""","video":"https://www.youtube.com/results?search_query=seated+thoracic+rotation+test"},
        {"id":"T2","name":"Chest Expansion Test","goal":"흉곽 확장성 및 호흡 기능 평가","method":"""
**준비 자세:** 환자는 바르게 섭니다. 줄자를 준비합니다.

**검사 순서:**
1. 흉골 검상돌기 높이(4번째 갈비뼈 간격)에 줄자를 두릅니다
2. 최대 호기(숨을 완전히 내쉰) 상태에서 둘레를 측정합니다
3. 최대 흡기(숨을 최대한 들이쉰) 상태에서 둘레를 측정합니다
4. 두 값의 차이를 계산합니다

**정상 기준:** 5cm 이상 차이
**양성 판정:** 2.5cm 미만 → 흉곽 가동성 저하 의심
**임상 의미:** 강직성 척추염, 흉추 후만 과도, 호흡 패턴 이상""","video":"https://www.youtube.com/results?search_query=chest+expansion+test+thoracic"},
        {"id":"T3","name":"Thoracic Kyphosis Assessment","goal":"흉추 후만 정도 평가","method":"""
**준비 자세:** 환자는 벽에 등을 대고 편안히 섭니다.

**검사 순서:**
1. 발뒤꿈치, 엉덩이, 어깨를 벽에 붙이도록 합니다
2. 뒷머리가 벽에 닿는지 확인합니다 (닿지 않으면 양성 의심)
3. 뒷머리와 벽 사이의 거리를 측정합니다
4. 측면에서 사진 촬영 후 Cobb 각도 시각 평가를 시행합니다

**정상 기준:** 머리가 벽에 닿음, 흉추 후만 20~40°
**양성 판정:** 뒷머리-벽 거리 3cm 이상 또는 과도한 전두부 전방 이동
**임상 의미:** 라운드숄더, 두부 전방 이동, 요통/어깨 통증과 연관""","video":"https://www.youtube.com/results?search_query=thoracic+kyphosis+assessment+posture"},
    ],

    "코어 안정성 (Core Stability)": [
        {"id":"CO1","name":"McGill Torso Endurance Test","goal":"코어 근지구력 평가 (굴곡/신전/측면)","method":"""
**① 굴곡 지구력 (Flexion Endurance):**
1. 등받이 60° 기울인 쐐기에 등을 기댑니다
2. 팔짱을 끼고 무릎 90° 굴곡 자세 유지
3. 등받이를 5cm 뒤로 이동 → 자세 유지 시간 측정
4. 자세 무너질 때까지 기록

**② 신전 지구력 (Extension Endurance):**
1. 테이블 끝에 엎드려 상체를 공중에 수평으로 유지
2. 팔짱 끼고 유지 시간 측정

**③ 측면 지구력 (Side Bridge):**
1. 한쪽 팔꿈치로 사이드 플랭크 자세
2. 유지 시간 측정, 양쪽 비교

**정상 기준 (건강한 성인):** 굴곡 136초 / 신전 161초 / 측면 95초
**불균형 지표:** 굴곡:신전 비 >1.0 또는 좌우 측면 비 >0.05 → 손상 위험""","video":"https://www.youtube.com/results?search_query=McGill+torso+endurance+test+core"},
        {"id":"CO2","name":"Dead Bug / Bird Dog Test","goal":"요추 안정화 조절 능력 평가","method":"""
**Dead Bug:**
1. 앙와위로 눕고 팔을 수직으로 올립니다
2. 무릎을 90°로 들어올립니다
3. 반대편 팔-다리를 동시에 천천히 내립니다 (요추 중립 유지)
4. 요추가 바닥에서 뜨거나 골반이 기울면 양성

**Bird Dog:**
1. 네발기기 자세 (테이블탑)
2. 반대편 팔-다리를 동시에 수평으로 뻗습니다
3. 몸통 회전 없이 10초 유지
4. 좌우 각 10회 반복 시 안정성 평가

**양성 판정:** 요추 과전만, 몸통 회전, 골반 측방 이동 발생 시
**임상 의미:** 심층 안정화 근육(다열근, 복횡근) 기능 저하""","video":"https://www.youtube.com/results?search_query=dead+bug+bird+dog+core+stability+test"},
        {"id":"CO3","name":"Plank / Side Plank Test","goal":"코어 지구력 평가","method":"""
**Plank (전방 플랭크):**
1. 전완을 바닥에 대고 발끝으로 지지합니다
2. 머리-어깨-엉덩이-발뒤꿈치 일직선 유지
3. 유지 시간 측정 (자세 무너질 때까지)

**Side Plank (측면 플랭크):**
1. 한쪽 전완으로 지지, 발은 겹치거나 나란히
2. 어깨-엉덩이-발목 일직선 유지
3. 유지 시간 측정, 양측 비교

**평가 기준 (성인):**
- 플랭크: 60초 이상 정상 / 30초 미만 취약
- 사이드 플랭크: 45초 이상 정상
- 좌우 차이 15% 이상: 불균형

**관찰 포인트:** 엉덩이 하강, 요추 처짐, 목 앞으로 빠짐""","video":"https://www.youtube.com/results?search_query=plank+side+plank+endurance+test"},
        {"id":"CO4","name":"Pelvic Tilt Control Test","goal":"골반 경사 조절 인지력 평가","method":"""
**준비 자세:** 환자는 등을 벽에 기대고 무릎을 약간 굽혀 섭니다.

**검사 순서:**
1. 요추와 벽 사이의 공간을 확인합니다 (손이 들어가는지)
2. 골반을 전방 경사(허리 앞으로) → 후방 경사(허리 납작) 번갈아 시행
3. 중립 위치에서 10초 유지하도록 합니다
4. 능동적으로 중립을 찾고 유지하는 능력을 평가합니다

**양성 판정:** 중립 골반 인지 불가, 과전만 또는 과후만 고착
**임상 의미:** 요통, 고관절 충돌, 슬관절 정렬 이상의 원인 파악""","video":"https://www.youtube.com/results?search_query=pelvic+tilt+control+neutral+spine"},
    ],

    "기능적 움직임 (Functional Movement)": [
        {"id":"F1","name":"Overhead Squat Test","goal":"전신 가동성 및 보상 작용 확인","method":"""
**준비 자세:** 환자는 어깨너비로 서고 팔을 머리 위로 완전히 뻗습니다.

**검사 순서:**
1. 팔을 머리 위로 뻗은 채 스쿼트를 내려갑니다
2. 발뒤꿈치가 바닥에서 뜨지 않고 최대한 깊이 내려갑니다
3. 전면/측면/후면에서 관찰합니다

**관찰 포인트:**
- 발: 외회전, 발뒤꿈치 들림
- 무릎: 내측 함몰 (knee valgus)
- 몸통: 과도한 전방 기울임
- 팔: 앞으로 쓰러짐

**보상 패턴 → 원인:**
무릎 내측 함몰 → 중둔근/외회전근 약화
발뒤꿈치 들림 → 종아리 단축
팔 앞으로 → 흉추/어깨 가동성 부족""","video":"https://www.youtube.com/results?search_query=overhead+squat+assessment+FMS"},
        {"id":"F2","name":"Single Leg Squat Test","goal":"하지 정렬 및 중둔근 조절력","method":"""
**준비 자세:** 한발로 서서 반대쪽 발을 살짝 들어올립니다.

**검사 순서:**
1. 한발 스쿼트를 천천히 시행합니다 (60° 굴곡 목표)
2. 전면에서 무릎 정렬을 관찰합니다
3. 측면에서 몸통 기울기를 관찰합니다
4. 5회 반복, 양측 비교합니다

**관찰 포인트:**
- 무릎 내측 함몰 (valgus) → 중둔근/VMO 약화
- 골반 반대편 하강 (Trendelenburg) → 지지측 중둔근 약화
- 몸통 과도한 전방 기울임 → 고관절 굴곡근 단축
- 발목 안쪽 무너짐 → 후경골근/발목 안정성 문제""","video":"https://www.youtube.com/results?search_query=single+leg+squat+test+assessment"},
        {"id":"F3","name":"In-line Lunge","goal":"균형 및 하지 가동성·안정성","method":"""
**준비 자세:** 발 길이만큼 앞뒤로 벌리고 섭니다. 막대기를 등 뒤에 세로로 붙입니다(있다면).

**검사 순서:**
1. 뒷발 무릎이 앞발 뒤꿈치 바로 뒤에 닿도록 런지를 내려갑니다
2. 막대기가 몸통과 3점 접촉 유지 (뒷머리, 등, 엉덩이)
3. 앞무릎이 발 정렬에서 벗어나지 않게 합니다
4. 좌우 각 3회 시행합니다

**양성 판정 (FMS 기준):**
- 0점: 통증 발생
- 1점: 자세 유지 불가
- 2점: 보상 움직임 있음
- 3점: 완벽한 수행

**임상 의미:** 고관절 굴곡근 유연성, 발목 가동성, 균형 능력 통합 평가""","video":"https://www.youtube.com/results?search_query=FMS+inline+lunge+test"},
        {"id":"F4","name":"Y-Balance Test","goal":"동적 균형 감각 및 부상 예측","method":"""
**준비 자세:** 중앙 발판에 한발로 서고 3방향 리치 선을 준비합니다.

**검사 순서:**
1. 전방(Anterior): 발끝 방향으로 최대한 뻗기
2. 후내측(Posteromedial): 뒤 안쪽으로 최대한 뻗기
3. 후외측(Posterolateral): 뒤 바깥쪽으로 최대한 뻗기
4. 각 방향 3회 시행, 최대 거리 기록
5. 복합점수: (전방+후내측+후외측) ÷ (하지길이×3) × 100

**판단 기준:**
- 복합점수 < 89% → 부상 위험 4배 증가
- 좌우 전방 차이 > 4cm → 부상 위험 2.5배 증가
- 전방 낮음 → 발목/무릎 / 후방 낮음 → 고관절/코어""","video":"https://www.youtube.com/results?search_query=Y+balance+test+dynamic+balance"},
    ],

    "신경역동학 (Neurodynamics)": [
        {"id":"N4","name":"ULTT2 (Radial Nerve)","goal":"요골신경 긴장도 확인","method":"""
**준비 자세:** 환자는 검사대에 눕습니다. 검사자는 환자 옆에 섭니다.

**검사 순서:**
1. 견갑대를 아래로 눌러 고정합니다
2. 팔꿈치를 신전시킵니다
3. 전완을 회내(손바닥 아래)시킵니다
4. 손목을 굴곡시킵니다
5. 어깨를 내회전·내전시킵니다
6. 고개를 반대편으로 측굴하여 증상 변화 확인합니다

**양성 판정:** 엄지/손등 방사통, 저림 발생 또는 고개 측굴 시 증상 변화
**임상 의미:** 요골신경 포착 또는 경추 신경근 (C6~C7) 병변""","video":"https://www.youtube.com/results?search_query=ULTT2+radial+nerve+tension+test"},
        {"id":"N5","name":"ULTT3 (Ulnar Nerve)","goal":"척골신경 긴장도 확인","method":"""
**준비 자세:** 환자는 검사대에 눕습니다.

**검사 순서:**
1. 견갑대를 아래로 눌러 고정합니다
2. 어깨를 90° 외전, 외회전시킵니다
3. 전완을 회외(손바닥 위)시킵니다
4. 손목을 신전시킵니다
5. 팔꿈치를 굴곡시킵니다 (귀 쪽으로)
6. 고개를 반대편으로 측굴하여 증상 변화 확인합니다

**양성 판정:** 4~5번째 손가락 저림, 팔꿈치 내측 통증 발생
**임상 의미:** 척골신경 포착 (주두 터널) 또는 C8~T1 신경근 병변""","video":"https://www.youtube.com/results?search_query=ULTT3+ulnar+nerve+tension+test"},
        {"id":"N6","name":"Femoral Nerve Slump Test","goal":"대퇴신경 긴장도 확인","method":"""
**준비 자세:** 환자는 복와위(엎드려)로 눕습니다.

**검사 순서:**
1. 환자의 무릎을 굴곡시킵니다 (발뒤꿈치 → 엉덩이 방향)
2. 동시에 고관절을 약간 신전시킵니다
3. 허벅지 앞쪽(대퇴사두근 부위)으로 방사되는 통증/저림 확인
4. 경추 굴곡 추가 시 증상 변화 확인합니다

**양성 판정:** 허벅지 앞쪽 방사통/저림 발생 시
**임상 의미:** L2~L4 신경근 병변, 대퇴신경 포착 또는 긴장""","video":"https://www.youtube.com/results?search_query=femoral+nerve+tension+test+prone"},
    ],

    "뇌신경-퍼포먼스 (Neuro-Performance)": [
        {"id":"NP1","name":"NPC (Near Point of Convergence)","goal":"시각 수렴 신경 기능 평가","method":"""
**준비물:** 펜 또는 작은 물체

**검사 순서:**
1. 펜을 환자 눈에서 40cm 앞에 놓습니다
2. 환자에게 펜을 바라보게 하면서 천천히 코 방향으로 가져옵니다
3. 한쪽 눈이 바깥쪽으로 돌아가거나(외편위) 두 개로 보인다고 할 때의 거리를 측정합니다
4. 다시 멀어지면서 하나로 보이는 회복 지점도 기록합니다

**정상 기준:** 파열점 6cm 이하, 회복점 10cm 이하
**양성 판정:** 파열점 10cm 초과
**임상 의미:** 집중력 저하, 어지러움, 읽기 어려움, 뇌진탕 후 주요 지표""","video":"https://www.youtube.com/results?search_query=near+point+convergence+test+NPC"},
        {"id":"NP2","name":"VOMS (Vestibular/Ocular Motor Screening)","goal":"시각-전정 협응 기능 평가","method":"""
**각 항목 시행 전후 증상(0~10점) 기록**

**① Smooth Pursuit (부드러운 추적):**
손가락을 좌우/상하로 천천히 움직이며 눈으로 추적 (속도: 1m를 2초에)

**② Saccade (빠른 안구 이동):**
두 목표물 사이를 빠르게 번갈아 보기 (수평/수직)

**③ Convergence (수렴):**
NPC 검사 동일하게 시행

**④ VOR (전정-안반사):**
목표물 고정 후 고개를 좌우로 빠르게 흔들기 (2Hz)

**⑤ Visual Motion Sensitivity:**
큰 격자 패턴 앞에서 좌우로 걷기

**양성 판정:** 각 항목에서 증상 2점 이상 증가
**임상 의미:** 뇌진탕 평가, 전정 기능 장애, 어지럼 원인 감별""","video":"https://www.youtube.com/results?search_query=VOMS+vestibular+ocular+motor+screening"},
        {"id":"NP3","name":"DVA (Dynamic Visual Acuity)","goal":"움직임 속 시야 안정 능력 평가","method":"""
**준비물:** 시력표 (2.5~4m 거리), 메트로놈 (120bpm)

**검사 순서:**
1. **정적 시력 측정:** 머리 고정 상태에서 읽을 수 있는 가장 작은 줄 기록
2. **동적 시력 측정:** 메트로놈 120bpm에 맞춰 고개를 좌↔우로 흔들며 (2Hz) 시력표 읽기
3. 두 값의 차이(줄 수) 계산

**결과 해석:**
- 0~1줄 차이: 정상
- 1줄 이상 감소: VOR 기능 저하 의심 → VOR 강화 훈련 필요

**임상 의미:** 운동 중 어지러움, 멀미, 집중력 저하, 스포츠 퍼포먼스 저하와 연관""","video":"https://www.youtube.com/results?search_query=dynamic+visual+acuity+DVA+test+vestibular"},
        {"id":"NP4","name":"Head Impulse Test (VOR Quick)","goal":"말초 전정계 기능 빠른 선별","method":"""
**준비 자세:** 환자는 검사자의 코를 바라봅니다.

**검사 순서:**
1. 검사자는 환자의 머리를 양손으로 잡습니다
2. 목표물(검사자 코)을 주시하게 합니다
3. 예고 없이 머리를 한쪽으로 빠르게 10~15° 회전시킵니다
4. 시선이 목표물에서 이탈하는지 관찰합니다
5. 양쪽 모두 시행합니다

**양성 판정:** 머리 회전 후 시선이 이탈하고 따라오는 교정안구운동(saccade) 발생 시
**임상 의미:** 반규관 또는 전정신경 기능 저하 → 균형·퍼포먼스 저하""","video":"https://www.youtube.com/results?search_query=head+impulse+test+VOR+vestibular"},
        {"id":"NP5","name":"Reactive Step Test","goal":"뇌-근육 반응 속도 및 낙상 위험 평가","method":"""
**준비 자세:** 환자는 편안히 서 있습니다 (발은 골반 너비, 맨발 또는 미끄럼 방지 신발).

**검사 순서:**
1. 검사자는 예고 없이 환자의 가슴/등/어깨 중 한 곳을 갑작스럽게 밀어 자극합니다
2. 환자가 내딛는 발의 반응 속도와 방향을 관찰합니다
3. 여러 방향에서 3~5회 시행합니다

**평가 기준:**
- 좋은 반응: 즉각 1스텝으로 안정화, 밀린 방향으로 정확히 반응
- 나쁜 반응: 여러 걸음 필요, 스텝 지연, 잘못된 방향 반응

**임상 의미:**
스텝 지연 → CNS 반응 속도 저하 / 여러 스텝 → 하지 근력/균형 저하
노인 낙상 위험 평가 및 스포츠 민첩성 지표""","video":"https://www.youtube.com/results?search_query=reactive+step+test+balance+perturbation"},
        {"id":"NP6","name":"TUG + Cognitive Dual Task","goal":"걷기 중 주의 분배 능력 평가","method":"""
**준비물:** 의자, 3m 표시 테이프, 타이머

**검사 순서:**
1. **기본 TUG:** 의자에서 일어나 → 3m 걷기 → 돌아오기 → 앉기 (시간 측정)
2. **듀얼 태스크 TUG:** 동일 동작 + 동시에 인지 과제 수행
   - 인지 과제 예: "100에서 3씩 빼기" 또는 동물 이름 말하기

**결과 해석:**
- 시간 10~20% 증가: 정상 범위
- 20% 이상 악화: 듀얼태스크 결함 (전정+실행기능 저하)
- 동작 비틀림/불안정 증가: 균형 통합 문제
- 인지 오류 증가: 주의 처리 결함

**임상 의미:** 낙상 위험, 스포츠 상황 판단 능력, 뇌진탕 후 평가""","video":"https://www.youtube.com/results?search_query=TUG+cognitive+dual+task+test"},
        {"id":"NP7","name":"Single Leg Stance (눈 뜸/감기)","goal":"발목-무릎 고유수용성 + 전정계 평가","method":"""
**준비 자세:** 환자는 맨발로 평평한 바닥에 섭니다.

**검사 순서:**
1. 한발로 서서 **눈 뜬 상태** 30초 유지 (시간 측정)
2. 동일한 발로 **눈 감은 상태** 30초 유지 (시간 측정)
3. 반대편도 동일하게 시행합니다
4. 흔들림, 발 이동, 지면 접촉 오류 횟수를 기록합니다

**정상 기준:**
- 눈 뜸: 30초 완수 (60세 이상 20초)
- 눈 감음: 20초 이상 (60세 이상 10초)

**임상 의미:**
눈 뜸 불안정 → 고유수용감각 저하 / 눈 감음 불안정 → 전정계 문제""","video":"https://www.youtube.com/results?search_query=single+leg+stance+test+balance+eyes+closed"},
    ],

    "ROM (관절가동범위)": [
        {"id":"R1","name":"경추 ROM","goal":"경추 6방향 가동범위 측정","method":"""
**측정 방법 (각도계 또는 CROM 기기 사용):**

1. **굴곡 (Flexion):** 턱을 가슴 방향으로 → 정상 45~50°
2. **신전 (Extension):** 천장 방향으로 → 정상 45~60°
3. **우측굴 (R. Lateral Flexion):** 귀를 어깨 방향으로 → 정상 45°
4. **좌측굴 (L. Lateral Flexion):** 반대편 → 정상 45°
5. **우회전 (R. Rotation):** 턱을 어깨 방향으로 → 정상 60~80°
6. **좌회전 (L. Rotation):** 반대편 → 정상 60~80°

**기록:** 각 방향 각도, 통증 발생 각도, 좌우 비대칭 여부
**임상 의미:** 제한 패턴으로 관절, 근육, 신경 문제 감별""","video":"https://www.youtube.com/results?search_query=cervical+ROM+measurement+goniometer"},
        {"id":"R2","name":"견관절 ROM","goal":"어깨 가동범위 측정","method":"""
**측정 방법 (각도계 사용):**

1. **굴곡 (Flexion):** 팔을 앞으로 → 정상 170~180°
2. **신전 (Extension):** 팔을 뒤로 → 정상 50~60°
3. **외전 (Abduction):** 팔을 옆으로 → 정상 170~180°
4. **내회전 (IR):** 팔꿈치 90° 후 전완 아래 → 정상 60~80°
5. **외회전 (ER):** 팔꿈치 90° 후 전완 위 → 정상 80~90°
6. **수평 내전:** 팔 수평으로 가슴 방향 → 정상 130°

**주요 임상 패턴:**
외회전 제한 + 내회전 제한 → 유착성 관절낭염
외전 제한 + 통증 → 충돌증후군""","video":"https://www.youtube.com/results?search_query=shoulder+ROM+measurement+goniometer"},
        {"id":"R3","name":"요추 ROM","goal":"요추 가동범위 측정","method":"""
**측정 방법:**

1. **굴곡 (Flexion):** 앞으로 굽히기 → 손가락-바닥 거리(cm) 또는 Schober test
   - Schober: S1에서 10cm 위 표시 → 굴곡 후 15cm 이상이면 정상
2. **신전 (Extension):** 뒤로 젖히기 → 정상 20~30°
3. **측굴 (Lateral Flexion):** 옆으로 굽히기 → 정상 30~40° (양측)
4. **회전 (Rotation):** 앉아서 몸통 회전 → 정상 35~45° (양측)

**기록:** 각 방향 제한, 통증 발생 방향, 증상 악화 패턴""","video":"https://www.youtube.com/results?search_query=lumbar+ROM+measurement+assessment"},
        {"id":"R4","name":"슬관절 ROM","goal":"무릎 가동범위 측정","method":"""
**측정 방법 (각도계 사용):**

1. **굴곡 (Flexion):** 무릎 최대 굴곡 → 정상 130~150°
2. **신전 (Extension):** 무릎 완전 신전 → 정상 0° (과신전 -5~-10°)

**측정 자세:**
- 앙와위: 고관절 굴곡 90° 상태에서 무릎 굴곡 측정
- 복와위: 무릎 최대 굴곡 측정

**임상 패턴:**
- 굴곡 제한: 관절강직, 슬개 주위 구축
- 신전 제한: 슬굴곡근 단축, 관절 삼출""","video":"https://www.youtube.com/results?search_query=knee+ROM+goniometer+measurement"},
        {"id":"R5","name":"족관절 ROM","goal":"발목 가동범위 측정","method":"""
**측정 방법 (각도계 사용):**

1. **배측굴곡 (Dorsiflexion):** 발등 들기
   - 무릎 신전 시: 정상 20° (비복근 평가)
   - 무릎 굴곡 시: 정상 30° (가자미근 평가)
   - Silfverskiold Test: 무릎 굴곡/신전 비교로 단축 부위 감별
2. **족저굴곡 (Plantarflexion):** 발끝 내리기 → 정상 45~50°
3. **내번 (Inversion):** 발안쪽 들기 → 정상 35°
4. **외번 (Eversion):** 발바깥쪽 들기 → 정상 15~20°

**임상 의미:** 배측굴곡 제한 → 종아리 단축, 발목 불안정성, 과사용 손상""","video":"https://www.youtube.com/results?search_query=ankle+ROM+measurement+dorsiflexion"},
    ],

    "MMT (도수근력검사)": [
        {"id":"M1","name":"MMT — 경추/어깨 근군","goal":"경추 및 견관절 주요 근육 도수근력 측정","method":"""
**MMT 등급 기준:**
- 5/5: 정상 — 최대 저항에 대해 완전한 가동범위 유지
- 4/5: 양호 — 중등도 저항 가능
- 3/5: 보통 — 중력 대항 가동범위 완수 (무저항)
- 2/5: 불량 — 중력 제거 시 가동범위 완수
- 1/5: 흔적 — 근 수축 촉지되나 움직임 없음
- 0/5: 무반응

**검사 근육:**
1. **경추 굴곡근** (흉쇄유돌근): 앙와위 두부 거상 저항
2. **경추 신전근** (두판상근): 복와위 두부 신전 저항
3. **승모근 상부**: 어깨 으쓱(거상) 저항
4. **삼각근 전방**: 팔 전방 굴곡 90° 저항
5. **극상근**: 빈 캔 자세 외전 저항
6. **극하근/소원근**: 팔꿈치 90° 굴곡 외회전 저항
7. **견갑하근**: Lift-off 자세 내회전 저항""","video":"https://www.youtube.com/results?search_query=MMT+manual+muscle+testing+shoulder+cervical"},
        {"id":"M2","name":"MMT — 요추/하지 근군","goal":"요추 및 하지 주요 근육 도수근력 측정","method":"""
**MMT 등급 기준 (위와 동일)**

**검사 근육:**
1. **장요근** (고관절 굴곡): 앉은 자세 고관절 굴곡 저항
2. **중둔근** (고관절 외전): 측와위 고관절 외전 저항
3. **대둔근** (고관절 신전): 복와위 고관절 신전 저항
4. **대퇴사두근** (슬관절 신전): 앉은 자세 슬관절 신전 저항
5. **슬굴곡근** (슬관절 굴곡): 복와위 슬관절 굴곡 저항
6. **전경골근** (족관절 배측굴곡): 배측굴곡 저항
7. **비복근/가자미근** (족관절 족저굴곡): 발뒤꿈치 들기 저항

**신경근 레벨 참고:**
L2~L3: 장요근 / L4: 전경골근 / L5: 단신근 / S1: 비복근""","video":"https://www.youtube.com/results?search_query=MMT+manual+muscle+testing+lower+extremity"},
    ],
}

# ── Session State ─────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "recommended_ids": [],
        "test_results": {},
        "prescription_weeks": {},
        "step1_done": False,
        "body_map_selected": [],
        "vas": 5,
        "pain_types": [],
        "details": "",
        "metabolic": [],
        "exercise_records": {},   # {week: {ex_name: {done,sets,notes}}}
        "saved_records": {},      # {week: {ex_name: {done,sets,notes}}} — 저장된 기록
        "custom_exercises": {},   # {week: [{name,sets,notes}]}
        "saved_custom": {},       # {week: [{name,sets,notes}]} — 저장된 추가운동
        "selected_week": 1,
        "members": {},            # {name: {info dict}}
        "loaded_member": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_client():
    if not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def calc_bmi(h, w):
    if h <= 0: return 0
    return round(w / ((h/100)**2), 1)

def bmi_label(bmi):
    if bmi < 18.5: return "저체중", "#3b82f6"
    elif bmi < 23: return "정상", "#16a34a"
    elif bmi < 25: return "과체중", "#f59e0b"
    elif bmi < 30: return "비만", "#ef4444"
    else: return "고도비만", "#7c3aed"

def normal_weight_range(h):
    hm = h / 100
    return round(18.5*hm**2, 1), round(22.9*hm**2, 1)

def get_intensity(age, vas, bmi):
    score = 0
    if age > 60: score += 2
    elif age > 45: score += 1
    if vas >= 7: score += 2
    elif vas >= 4: score += 1
    if bmi >= 30: score += 1
    if score >= 4: return "저강도 (Low)", "🟢"
    elif score >= 2: return "중강도 (Moderate)", "🟡"
    else: return "고강도 (High)", "🔴"

def recommend_tests(body_parts, vas, pain_types, details, metabolic, goal_types, body_map):
    client = get_client()
    if not client:
        st.error("⚠️ API 키가 설정되지 않았습니다.")
        return [], []

    # 선택된 모든 부위의 검사 합치기
    all_tests = []
    covered_parts = set()
    for bp in body_parts:
        tests = TEST_DB.get(bp, [])
        for t in tests:
            if t["id"] not in covered_parts:
                all_tests.append((bp, t))
                covered_parts.add(t["id"])

    # 바디맵 선택 부위 → 연관 DB 키 매핑
    bodymap_to_db = {
        "머리/얼굴": "뇌신경-퍼포먼스 (Neuro-Performance)",
        "뒷머리": "뇌신경-퍼포먼스 (Neuro-Performance)",
        "목 앞": "경추 (Cervical)", "목 뒤": "경추 (Cervical)",
        "가슴": "흉추 (Thoracic Spine)",
        "등(상부)": "흉추 (Thoracic Spine)",
        "등(하부)/요추": "요추 (Lumbar)",
        "복부": "코어 안정성 (Core Stability)",
        "어깨(앞)": "견관절 (Shoulder)", "어깨(뒤)": "견관절 (Shoulder)",
        "팔꿈치(앞)": "주관절 (Elbow)", "팔꿈치(뒤)": "주관절 (Elbow)",
        "손목/손": "수관절 (Wrist/Hand)",
        "고관절(앞)": "고관절 (Hip)", "엉덩이": "고관절 (Hip)",
        "무릎(앞)": "슬관절 (Knee)", "무릎(뒤)": "슬관절 (Knee)",
        "종아리": "족관절 (Ankle/Foot)",
        "발목/발": "족관절 (Ankle/Foot)",
        "발뒤꿈치": "족관절 (Ankle/Foot)",
    }
    for region in body_map:
        mapped_db = bodymap_to_db.get(region)
        if mapped_db and mapped_db in TEST_DB:
            for t in TEST_DB[mapped_db]:
                if t["id"] not in covered_parts:
                    all_tests.append((mapped_db, t))
                    covered_parts.add(t["id"])

    if not all_tests:
        return [], []

    test_summary = "\n".join(f"- {t['id']}: {t['name']} ({t['goal']}) [{bp}]" for bp, t in all_tests)
    prompt = f"""스포츠의학 전문가. 환자 정보로 가장 관련성 높은 검사 3~6개 ID만 반환.

목적: {', '.join(goal_types)} / 부위: {', '.join(body_parts)}
바디맵 통증 부위: {', '.join(body_map) or '없음'}
VAS: {vas}/10 / 통증: {', '.join(pain_types) or '미기재'}
대사질환: {', '.join(metabolic) or '없음'} / 증상: {details}

검사목록:
{test_summary}

반드시 이 형식으로만:
RECOMMENDED_IDS: ID1, ID2, ID3"""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role":"user","content":prompt}]
        )
        text = response.content[0].text
        match = re.search(r"RECOMMENDED_IDS:\s*([^\n]+)", text, re.IGNORECASE)
        all_valid = {t["id"] for _, t in all_tests}
        if match:
            ids = [x.strip() for x in re.split(r"[,\s]+", match.group(1)) if x.strip()]
            return [i for i in ids if i in all_valid], all_tests
        found = re.findall(r"\b([A-Z]\d{1,2})\b", text)
        return [i for i in found if i in all_valid][:6], all_tests
    except Exception as e:
        st.error(f"AI 오류: {e}")
        return [], []

def generate_week_program(week, patient_info, test_results, body_part, intensity_label):
    """특정 주차 운동 프로그램 생성"""
    client = get_client()
    if not client:
        return "API 키가 설정되지 않았습니다."

    # 주차별 단계 결정
    if week <= 2:
        phase = "Step 1: 가동성 (Mobility) — 통증 감소, 관절 가동범위 회복"
        focus = "부드러운 스트레칭, 열 적용, 관절 가동운동 위주"
    elif week <= 4:
        phase = "Step 2: 안정성 (Stability) — 국소 근육 활성화, 분절 안정화"
        focus = "코어 안정화, 낮은 강도의 등척성 운동"
    elif week <= 8:
        phase = "Step 3: 근신경 활성화 (Neuromuscular) — 기능적 패턴 훈련"
        focus = "복합 동작 패턴, 중등도 저항 운동"
    elif week <= 16:
        phase = "Step 4: 근력 강화 (Strength) — 점진적 과부하"
        focus = "저항 운동 점진적 증가, 기능적 훈련"
    elif week <= 20:
        phase = "Step 5: 기능적 통합 (Functional Integration)"
        focus = "스포츠 특이적 동작, 민첩성, 협응력"
    else:
        phase = "Step 6: 복귀 및 유지 (Return & Maintenance)"
        focus = "스포츠/직업 복귀 준비, 자가 관리 프로그램"

    results_str = "\n".join(f"- {tid}: {'양성(+)' if r=='양성(+)' else '음성(-)'}" for tid,r in test_results.items())
    is_diet = patient_info.get("goal_type","") == "다이어트"
    diet_add = "\n식단 권장사항도 간략히 포함해주세요." if is_diet else ""

    prompt = f"""You are an exercise prescription expert. Create a week {week} exercise program for this patient.

Patient: age {patient_info['age']}, BMI {patient_info['bmi']}, VAS {patient_info['vas']}/10
Area: {body_part}, Intensity: {intensity_label}
Conditions: {', '.join(patient_info.get('metabolic',[])) or 'none'}
Occupation: {patient_info.get('occupation','')}
Tests: {results_str}
Phase: {phase} / Focus: {focus}
{diet_add}

Respond ONLY with valid JSON, no extra text, no markdown:
{{"phase":"{phase}","week_goal":"one sentence goal in Korean","exercises":[{{"name":"운동명","icon_keyword":"스트레칭","sets":"3세트 x 15회","goal":"목적","method":"1. 시작자세 2. 동작 3. 주의","tip":"팁"}}],"precautions":"주의사항"}}

Rules:
- 4 to 5 exercises only
- All text values in Korean
- method field: use numbered list like "1. 자세 2. 동작 3. 주의" with spaces, NOT newlines
- NO special characters that break JSON (no quotes inside values, use spaces)
- intensity: {intensity_label}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2500,
            messages=[{"role":"user","content":prompt}]
        )
        text = response.content[0].text.strip()
        # 여러 방법으로 JSON 추출 시도
        # 방법1: 전체가 JSON
        try:
            return json.loads(text)
        except:
            pass
        # 방법2: ```json 블록
        json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_block:
            try:
                return json.loads(json_block.group(1))
            except:
                pass
        # 방법3: 첫번째 { } 추출
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            raw = json_match.group()
            # 줄바꿈을 공백으로 치환해서 파싱 시도
            cleaned = re.sub(r'(?<!\\)\n', ' ', raw)
            try:
                return json.loads(cleaned)
            except:
                pass
        # 방법4: 파싱 실패 시 텍스트를 그대로 표시
        return {"fallback_text": text}
    except Exception as e:
        return {"error": str(e)}

def generate_csv_full(patient_info, test_results, week_records, custom_exercises):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["=== 환자 정보 ==="])
    for k,v in patient_info.items():
        w.writerow([k, v])
    w.writerow([])
    w.writerow(["=== 검사 결과 ==="])
    for tid, res in test_results.items():
        w.writerow([tid, res])
    w.writerow([])
    w.writerow(["=== 운동 기록 ==="])
    for week, exercises in week_records.items():
        w.writerow([f"--- {week}주차 ---"])
        for ex, data in exercises.items():
            w.writerow([ex, f"수행: {data.get('done','')}", f"세트: {data.get('sets','')}", f"특이사항: {data.get('notes','')}"])
        if week in custom_exercises:
            for ex in custom_exercises[week]:
                w.writerow([f"[추가] {ex['name']}", ex.get('sets',''), ex.get('notes','')])
    return out.getvalue().encode("utf-8-sig")

# ── SIDEBAR v3.1 ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="app-title">🏥 재활 시스템</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-sub">AI Rehabilitation CDSS v3.1</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 회원 불러오기
    if st.session_state.members:
        st.markdown("**📂 저장된 회원 불러오기**")
        member_names = ["-- 새 회원 --"] + list(st.session_state.members.keys())
        sel_mem = st.selectbox("회원", member_names, label_visibility="collapsed")
        if sel_mem != "-- 새 회원 --" and st.button("📥 불러오기", use_container_width=True):
            m = st.session_state.members[sel_mem]
            for k in ["vas","pain_types","details","body_map_selected","exercise_records",
                      "saved_records","custom_exercises","saved_custom","test_results","prescription_weeks"]:
                mk = "body_map" if k == "body_map_selected" else k
                if mk in m: st.session_state[k] = m[mk]
            st.session_state.step1_done = bool(m.get("test_results"))
            st.success(f"✅ {sel_mem} 불러옴!")
        st.markdown("---")

    st.markdown("**👤 환자 기본 정보**")
    patient_name = st.text_input("이름", placeholder="홍길동", label_visibility="collapsed")
    if not patient_name:
        st.caption("👆 이름 입력")

    col_age, col_sex = st.columns(2)
    with col_age:
        patient_age = st.number_input("나이", min_value=1, max_value=120, value=30, step=1, label_visibility="collapsed")
        st.caption("나이")
    with col_sex:
        patient_sex = st.selectbox("성별", ["남","여"], label_visibility="collapsed")
        st.caption("성별")

    col_h, col_w = st.columns(2)
    with col_h:
        height = st.number_input("키", min_value=100, max_value=220, value=170, step=1, label_visibility="collapsed")
        st.caption("키 (cm)")
    with col_w:
        weight = st.number_input("몸무게", min_value=30, max_value=200, value=70, step=1, label_visibility="collapsed")
        st.caption("몸무게 (kg)")

    bmi = calc_bmi(height, weight)
    bl, bc = bmi_label(bmi)
    st.markdown(f"**BMI {bmi}** — <span style='color:{bc};font-weight:700'>{bl}</span>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**💼 직업**")
    occ = st.selectbox("직업", ["사무직","활동직","기타"], label_visibility="collapsed")
    if occ == "기타":
        occ_detail = st.text_input("직업명", placeholder="예: 요리사, 간호사...", label_visibility="collapsed")
        st.caption("직업 직접 입력")
    else:
        occ_detail = occ

    st.markdown("---")
    st.markdown("**🩺 대사질환**")
    metabolic = st.multiselect("대사질환", ["고혈압","당뇨","고지혈증","심장질환","골다공증","비만","갑상선 질환","기타"],
                               placeholder="선택...", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**🎯 검사 목적 (복수 선택)**")
    goal_types = st.multiselect("목적", ["근골격 재활","다이어트","체형교정","뇌신경 재활","뇌신경-퍼포먼스","코어/기능","ROM 측정","MMT","기타"],
                                default=["근골격 재활"], placeholder="선택...", label_visibility="collapsed")
    if not goal_types: goal_types = ["근골격 재활"]
    goal_type = goal_types[0]

    musculo_parts = [k for k in TEST_DB if k not in ["다이어트 / 체력검사","체형교정","뇌신경 (Neurological)","ROM (관절가동범위)","MMT (도수근력검사)","기능적 움직임 (Functional Movement)","코어 안정성 (Core Stability)","신경역동학 (Neurodynamics)","뇌신경-퍼포먼스 (Neuro-Performance)"]]
    special_map = {
        "다이어트":"다이어트 / 체력검사",
        "체형교정":"체형교정",
        "뇌신경 재활":"뇌신경 (Neurological)",
        "뇌신경-퍼포먼스":"뇌신경-퍼포먼스 (Neuro-Performance)",
        "코어/기능":"코어 안정성 (Core Stability)",
        "ROM 측정":"ROM (관절가동범위)",
        "MMT":"MMT (도수근력검사)",
    }
    auto_parts = [special_map[g] for g in goal_types if g in special_map]

    if "근골격 재활" in goal_types or "기타" in goal_types:
        st.markdown("**🦴 근골격 부위 (복수 선택)**")
        selected_musculo = st.multiselect("부위", musculo_parts, placeholder="부위 선택...", label_visibility="collapsed")
        body_parts = selected_musculo + auto_parts
    else:
        selected_musculo = []
        body_parts = auto_parts
    if not body_parts: body_parts = ["견관절 (Shoulder)"]
    body_part = body_parts[0]

    st.markdown("---")
    steps = [("1. 주관적 평가", st.session_state.step1_done),
             ("2. 객관적 평가", bool(st.session_state.test_results)),
             ("3. 운동 처방", bool(st.session_state.prescription_weeks))]
    for lbl, done in steps:
        st.markdown(f"{'✅' if done else '⬜'} {lbl}")

    st.markdown("---")
    if st.button("💾 회원 저장", use_container_width=True):
        if patient_name:
            st.session_state.members[patient_name] = {
                "name":patient_name,"age":patient_age,"sex":patient_sex,
                "height":height,"weight":weight,"bmi":bmi,
                "occupation":occ_detail or occ,"metabolic":metabolic,
                "goal_types":goal_types,"body_parts":body_parts,
                "vas":st.session_state.vas,"pain_types":st.session_state.pain_types,
                "details":st.session_state.details,"body_map":st.session_state.body_map_selected,
                "test_results":st.session_state.test_results,
                "prescription_weeks":st.session_state.prescription_weeks,
                "exercise_records":st.session_state.exercise_records,
                "saved_records":st.session_state.saved_records,
                "custom_exercises":st.session_state.custom_exercises,
                "saved_custom":st.session_state.saved_custom,
                "saved_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            st.success(f"✅ {patient_name} 저장!")
        else:
            st.warning("이름을 입력하세요.")

# ── MAIN ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="app-title">🏥 AI 맞춤형 운동재활 시스템</div>', unsafe_allow_html=True)
st.markdown('<div class="app-sub">초보 트레이너도 즉시 활용 가능한 임상 의사결정 지원 시스템 v3.0</div>', unsafe_allow_html=True)
st.markdown("---")

# BMI 카드 (다이어트)
if goal_type == "다이어트":
    low_w, high_w = normal_weight_range(height)
    diff = round(weight - high_w, 1)
    st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown("### 📊 BMI 분석")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric"><div class="metric-label">현재 BMI</div><div class="metric-value" style="color:{bc}">{bmi}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric"><div class="metric-label">판정</div><div class="metric-value" style="color:{bc}">{bl}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric"><div class="metric-label">정상 체중</div><div class="metric-value">{low_w}~{high_w}kg</div></div>', unsafe_allow_html=True)
    with c4:
        if diff > 0:
            st.markdown(f'<div class="metric"><div class="metric-label">감량 목표</div><div class="metric-value" style="color:#dc2626">-{diff}kg</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="metric"><div class="metric-label">상태</div><div class="metric-value" style="color:#16a34a">정상✓</div></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📋 Step 1 — 주관적 평가", "🔍 Step 2 — 객관적 평가", "💊 Step 3 — 운동 처방"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: 주관적 평가
# ──────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 📋 주관적 평가")

    with st.expander("🗺️ 통증 바디맵 — 아픈 부위 선택", expanded=True):
        body_regions = {
            "앞면": ["머리/얼굴","목 앞","가슴","복부","어깨(앞)","팔꿈치(앞)","손목/손","고관절(앞)","무릎(앞)","발목/발"],
            "뒷면": ["뒷머리","목 뒤","등(상부)","등(하부)/요추","어깨(뒤)","팔꿈치(뒤)","엉덩이","무릎(뒤)","종아리","발뒤꿈치"]
        }
        selected_regions = list(st.session_state.body_map_selected)
        bm_cols = st.columns(2)
        for i,(side,regions) in enumerate(body_regions.items()):
            with bm_cols[i]:
                st.markdown(f"**{side}**")
                for region in regions:
                    checked = st.checkbox(region, value=(region in selected_regions), key=f"bm_{region}")
                    if checked and region not in selected_regions: selected_regions.append(region)
                    elif not checked and region in selected_regions: selected_regions.remove(region)
        st.session_state.body_map_selected = selected_regions
        if selected_regions:
            st.info(f"📍 선택 부위: **{', '.join(selected_regions)}**")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**😣 통증 강도 (VAS)**")
        vas = st.slider("VAS", 0, 10, st.session_state.vas, key="vas_slider", label_visibility="collapsed")
        st.session_state.vas = vas
        color = "#dc2626" if vas>=7 else "#f59e0b" if vas>=4 else "#16a34a"
        vas_text = "심한 통증" if vas>=7 else "중등도 통증" if vas>=4 else "경미한 통증" if vas>0 else "통증 없음"
        st.markdown(f'<div style="text-align:center;font-size:2.2rem;color:{color};font-weight:700;padding:8px">{vas}/10<br><span style="font-size:0.85rem">{vas_text}</span></div>', unsafe_allow_html=True)

    with col2:
        st.markdown("**🔥 통증 양상**")
        pain_types = st.multiselect("통증양상", ["날카로운 통증(Sharp)","저린감(Numbness)","둔한 통증(Dull)","타는 느낌(Burning)","욱신거림(Throbbing)","방사통(Radiating)","야간통(Night Pain)","운동 시 악화"],
                                    default=st.session_state.pain_types, placeholder="해당 항목 선택...", label_visibility="collapsed")
        st.session_state.pain_types = pain_types

    st.markdown("**📝 상세 증상 및 병력**")
    details = st.text_area("증상", value=st.session_state.details, height=100,
                           placeholder="예: 3주 전 야구 중 어깨 통증. 팔 들면 악화. 3년 전 SLAP 수술 이력.",
                           label_visibility="collapsed")
    st.session_state.details = details

    intensity_label, intensity_icon = get_intensity(patient_age, vas, bmi)
    st.info(f"💪 자동 산출 운동 강도: {intensity_icon} **{intensity_label}** (나이 {patient_age}세 · VAS {vas} · BMI {bmi})")

    if metabolic:
        st.warning(f"⚠️ 대사질환: {', '.join(metabolic)} — 처방 시 금기사항 자동 반영")

    st.markdown("---")
    if st.button("🤖 AI 검사 추천 받기", use_container_width=True):
        if not patient_name:
            st.warning("환자 이름을 입력해 주세요.")
        elif not details:
            st.warning("상세 증상을 입력해 주세요.")
        else:
            with st.spinner("AI 분석 중... (3~5초)"):
                ids, all_tests = recommend_tests(body_parts, vas, pain_types, details, metabolic, goal_types, selected_regions)
                st.session_state["all_tests_lookup"] = {t["id"]: (bp, t) for bp, t in all_tests}
            if ids:
                st.session_state.recommended_ids = ids
                st.session_state.test_results = {}
                st.session_state.prescription_weeks = {}
                st.session_state.step1_done = True
                st.success(f"✅ 추천 검사 {len(ids)}개: **{', '.join(ids)}** — Step 2 탭으로 이동하세요!")
                st.balloons()
            else:
                st.error("검사 추천 실패. 증상을 더 자세히 입력하거나 API 키를 확인하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: 객관적 평가
# ──────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🔍 객관적 평가")
    if not st.session_state.recommended_ids:
        st.info("ℹ️ Step 1에서 AI 검사 추천을 먼저 진행해 주세요.")
    else:
        # 전체 테스트 DB에서 ID로 검색
        all_test_lookup = {}
        for bp, tests in TEST_DB.items():
            for t in tests:
                all_test_lookup[t["id"]] = t

        rec_tests = [all_test_lookup[i] for i in st.session_state.recommended_ids if i in all_test_lookup]
        st.markdown(f"**추천 검사 {len(rec_tests)}개**")
        if metabolic:
            st.warning(f"⚠️ 검사 전: {', '.join(metabolic)} — 혈압/혈당 확인 후 시행")

        results = {}
        for test in rec_tests:
            with st.expander(f"🔬 **[{test['id']}] {test['name']}**", expanded=True):
                col_m, col_r = st.columns([3,1])
                with col_m:
                    # 심플하고 빠르게 읽을 수 있는 방식으로 표시
                    raw = test["method"]
                    # **준비 자세:** 이후 첫 문장만, 검사 순서 번호 추출
                    prep = re.search(r"\*\*준비 자세:\*\*(.+?)(?:\n|$)", raw)
                    steps_raw = re.findall(r"(\d+)\.\s+(.+?)(?=\n\d+\.|\n\*\*|$)", raw, re.DOTALL)
                    positive = re.search(r"\*\*양성 판정:\*\*(.+?)(?:\n|$)", raw)
                    caution  = re.search(r"\*\*[⚠️임상 의미주의]+[^:]*:\*\*(.+?)(?:\n|$)", raw)

                    st.markdown(f"🎯 **{test['goal']}**")
                    if prep:
                        st.caption(f"📍 준비: {prep.group(1).strip()}")
                    if steps_raw:
                        steps_text = " → ".join([f"**{n}.** {s.strip()[:40]}" for n,s in steps_raw[:4]])
                        st.markdown(steps_text)
                    if positive:
                        st.markdown(f'<span style="background:#fee2e2;color:#b91c1c;border-radius:6px;padding:2px 8px;font-size:0.8rem">✅ 양성: {positive.group(1).strip()[:60]}</span>', unsafe_allow_html=True)
                    # 상세 보기 토글
                    with st.expander("📖 상세 방법 보기"):
                        st.markdown(raw)
                        st.markdown(f"[▶️ 영상]({test['video']})")

                with col_r:
                    prev = st.session_state.test_results.get(test["id"], "음성(-)")
                    result = st.radio("결과", ["양성(+)","음성(-)"],
                                     index=0 if prev=="양성(+)" else 1,
                                     key=f"r_{test['id']}", label_visibility="collapsed")
                    results[test["id"]] = result
                    badge = '<span class="pos">양성 (+)</span>' if result=="양성(+)" else '<span class="neg">음성 (-)</span>'
                    st.markdown(badge, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("✅ 결과 저장 후 처방으로 이동", use_container_width=True):
            st.session_state.test_results = results
            pos = sum(1 for v in results.values() if v=="양성(+)")
            st.success(f"저장 완료! 양성 {pos}개 / 음성 {len(results)-pos}개 — Step 3 탭으로 이동하세요!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: 운동 처방
# ──────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 💊 6개월 주기화 운동 프로그램")
    if not st.session_state.test_results:
        st.info("ℹ️ Step 2에서 검사 결과를 먼저 저장해 주세요.")
    else:
        bmi_val = calc_bmi(height, weight)
        intensity_label, intensity_icon = get_intensity(patient_age, st.session_state.vas, bmi_val)

        # 요약 메트릭
        total = len(st.session_state.test_results)
        pos   = sum(1 for v in st.session_state.test_results.values() if v=="양성(+)")
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(f'<div class="metric"><div class="metric-label">환자</div><div class="metric-value" style="font-size:1rem">{patient_name or "-"}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric"><div class="metric-label">VAS</div><div class="metric-value">{st.session_state.vas}/10</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric"><div class="metric-label">양성 검사</div><div class="metric-value">{pos}/{total}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="metric"><div class="metric-label">강도</div><div class="metric-value" style="font-size:1rem">{intensity_icon} {intensity_label.split()[0]}</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # 6개월 주차 선택 (4주 단위 그룹)
        st.markdown("#### 📅 주차 선택 — 클릭하면 해당 주차 프로그램 생성")

        phase_map = {
            (1,2): ("🟢 Phase 1: 가동성", "#dcfce7", "#15803d"),
            (3,4): ("🔵 Phase 2: 안정성", "#dbeafe", "#1d4ed8"),
            (5,8): ("🟡 Phase 3: 근신경 활성화", "#fef9c3", "#854d0e"),
            (9,16): ("🟠 Phase 4: 근력 강화", "#ffedd5", "#c2410c"),
            (17,20): ("🔴 Phase 5: 기능적 통합", "#fee2e2", "#991b1b"),
            (21,24): ("🟣 Phase 6: 복귀/유지", "#ede9fe", "#6d28d9"),
        }

        # 주차 버튼 그리드
        all_weeks = list(range(1, 25))
        cols = st.columns(8)
        for i, week in enumerate(all_weeks):
            with cols[i % 8]:
                is_generated = week in st.session_state.prescription_weeks
                label = f"✓{week}주" if is_generated else f"{week}주"
                if st.button(label, key=f"week_{week}", use_container_width=True):
                    st.session_state.selected_week = week

        st.markdown("---")

        selected_week = st.session_state.selected_week

        # 현재 선택 주차 표시
        for (w_start, w_end),(phase_name, bg, tc) in phase_map.items():
            if w_start <= selected_week <= w_end:
                st.markdown(f'<div style="background:{bg};color:{tc};border-radius:10px;padding:10px 16px;font-weight:700;margin-bottom:12px">{phase_name} — {selected_week}주차</div>', unsafe_allow_html=True)
                break

        patient_info_dict = {
            "name": patient_name, "age": patient_age,
            "height": height, "weight": weight, "bmi": bmi_val,
            "vas": st.session_state.vas,
            "pain_types": ", ".join(st.session_state.pain_types),
            "details": st.session_state.details,
            "metabolic": metabolic,
            "occupation": occ_detail or occ,
            "goal_type": goal_type,
        }

        # 생성 버튼
        btn_col1, btn_col2 = st.columns([3,1])
        with btn_col1:
            if st.button(f"🤖 {selected_week}주차 운동 프로그램 생성 (빠른 응답)", use_container_width=True):
                with st.spinner(f"{selected_week}주차 프로그램 생성 중... (약 5~10초)"):
                    result = generate_week_program(
                        selected_week, patient_info_dict,
                        st.session_state.test_results, body_part, intensity_label
                    )
                    st.session_state.prescription_weeks[selected_week] = result

        # 프로그램 표시
        if selected_week in st.session_state.prescription_weeks:
            prog = st.session_state.prescription_weeks[selected_week]

            if isinstance(prog, dict) and "fallback_text" in prog:
                st.markdown("#### 📄 운동 프로그램")
                st.markdown(prog["fallback_text"])
            elif isinstance(prog, dict) and "error" not in prog:
                st.markdown(f"**🎯 이번 주 목표:** {prog.get('week_goal','')}")
                exercises = prog.get("exercises", [])

                st.markdown("#### 🏋️ 운동 목록")
                ex_cols = st.columns(2)

                if selected_week not in st.session_state.exercise_records:
                    st.session_state.exercise_records[selected_week] = {}
                if selected_week not in st.session_state.custom_exercises:
                    st.session_state.custom_exercises[selected_week] = []

                # 저장된 기록 불러오기
                saved = st.session_state.saved_records.get(selected_week, {})

                temp_records = {}
                for idx, ex in enumerate(exercises):
                    with ex_cols[idx % 2]:
                        icon = get_exercise_icon(ex.get("icon_keyword", ex.get("name","")))
                        st.markdown(f"""
<div class="ex-card">
  <div class="ex-icon">{icon}</div>
  <div class="ex-name">{ex.get('name','')}</div>
  <div class="ex-goal">🎯 {ex.get('goal','')}</div>
  <div style="font-size:0.8rem;color:#2563eb;font-weight:600;margin-bottom:4px">⏱️ {ex.get('sets','')}</div>
  <div class="ex-method">{ex.get('method','').replace(chr(10),'<br>')}</div>
  <div style="font-size:0.78rem;color:#7c3aed;margin-top:6px">💡 {ex.get('tip','')}</div>
</div>""", unsafe_allow_html=True)

                        ex_name = ex.get("name","")
                        prev_rec = saved.get(ex_name, {})

                        with st.expander("📝 기록 입력"):
                            done = st.checkbox("수행 완료 ✅", value=(prev_rec.get("done","") == "✅"), key=f"done_{selected_week}_{idx}")
                            actual_sets = st.text_input("세트/횟수", value=prev_rec.get("sets",""), placeholder="예: 3x12", key=f"sets_{selected_week}_{idx}", label_visibility="collapsed")
                            st.caption("실제 수행 세트/횟수")
                            notes = st.text_input("특이사항", value=prev_rec.get("notes",""), placeholder="통증 변화, 느낌 등", key=f"notes_{selected_week}_{idx}", label_visibility="collapsed")
                            st.caption("특이사항 메모")
                            temp_records[ex_name] = {"done":"✅" if done else "⬜","sets":actual_sets,"notes":notes}

                # 저장 버튼 (명시적)
                st.markdown("---")
                save_col1, save_col2 = st.columns(2)
                with save_col1:
                    if st.button(f"💾 {selected_week}주차 기록 저장", use_container_width=True, key=f"save_rec_{selected_week}"):
                        st.session_state.saved_records[selected_week] = temp_records
                        st.session_state.exercise_records[selected_week] = temp_records
                        st.success(f"✅ {selected_week}주차 기록 저장 완료!")

                # 저장된 기록 보기
                with save_col2:
                    if saved and st.button(f"📋 저장된 기록 보기", use_container_width=True, key=f"view_rec_{selected_week}"):
                        st.session_state[f"show_rec_{selected_week}"] = not st.session_state.get(f"show_rec_{selected_week}", False)

                if st.session_state.get(f"show_rec_{selected_week}") and saved:
                    st.markdown(f"**📋 {selected_week}주차 저장 기록**")
                    for ex_n, rec in saved.items():
                        st.markdown(f"- {rec.get('done','⬜')} **{ex_n}** | {rec.get('sets','-')} | {rec.get('notes','-')}")

                # 운동 추가
                st.markdown("#### ➕ 운동 추가")
                with st.expander("운동 추가하기"):
                    add_col1, add_col2, add_col3 = st.columns([2,1,2])
                    with add_col1:
                        new_ex_name = st.text_input("운동명", placeholder="예: 덤벨 사이드레이즈", key=f"new_ex_{selected_week}", label_visibility="collapsed")
                        st.caption("운동명")
                    with add_col2:
                        new_ex_sets = st.text_input("세트", placeholder="3x15", key=f"new_sets_{selected_week}", label_visibility="collapsed")
                        st.caption("세트/횟수")
                    with add_col3:
                        new_ex_notes = st.text_input("메모", placeholder="메모", key=f"new_notes_{selected_week}", label_visibility="collapsed")
                        st.caption("메모")
                    if st.button("➕ 추가", key=f"add_btn_{selected_week}"):
                        if new_ex_name:
                            if selected_week not in st.session_state.custom_exercises:
                                st.session_state.custom_exercises[selected_week] = []
                            st.session_state.custom_exercises[selected_week].append(
                                {"name":new_ex_name,"sets":new_ex_sets,"notes":new_ex_notes}
                            )
                            st.success(f"'{new_ex_name}' 추가!")

                saved_custom = st.session_state.custom_exercises.get(selected_week, [])
                if saved_custom:
                    st.markdown("**추가된 운동:**")
                    for cex in saved_custom:
                        st.markdown(f"- ➕ **{cex['name']}** | {cex.get('sets','')} | {cex.get('notes','')}")

                if prog.get("precautions"):
                    st.warning(f"⚠️ 이번 주 주의사항: {prog['precautions']}")

            else:
                error_msg = prog.get("error", str(prog)) if isinstance(prog, dict) else str(prog)
                st.error(f"생성 오류: {error_msg}")

        # 전체 기록 저장
        st.markdown("---")
        st.markdown("#### 💾 전체 기록 저장")
        col_dl, col_print = st.columns(2)
        with col_dl:
            csv_data = generate_csv_full(
                {"환자명":patient_name,"나이":f"{patient_age}세","키":f"{height}cm","몸무게":f"{weight}kg",
                 "BMI":bmi_val,"직업":occ_detail or occ,"대사질환":", ".join(metabolic) or "없음",
                 "부위":body_part,"VAS":st.session_state.vas,"강도":intensity_label,
                 "기록일":datetime.now().strftime("%Y-%m-%d %H:%M")},
                st.session_state.test_results,
                st.session_state.exercise_records,
                st.session_state.custom_exercises
            )
            fname = f"재활기록_{patient_name}_{datetime.now().strftime('%Y%m%d')}.csv"
            st.download_button("📥 전체 기록 CSV 다운로드", data=csv_data, file_name=fname, mime="text/csv", use_container_width=True)
        with col_print:
            generated_weeks = sorted(st.session_state.prescription_weeks.keys())
            if generated_weeks:
                st.info(f"생성된 주차: {', '.join(str(w)+'주' for w in generated_weeks)}")
