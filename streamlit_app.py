import pandas as pd
import streamlit as st

from student_analysis import EDUCATION_ORDER, FACTORS, LABELS, SCORES, load_data, show_metrics


st.set_page_config(page_title="학생 성적 탐색", page_icon="📊", layout="wide")


def reset_filters():
    for column in FACTORS:
        st.session_state.pop(f"filter_{column}", None)
    st.session_state.pop("score_range", None)


def change_file():
    reset_filters()
    st.session_state.pop("student_data", None)
    st.session_state.pop("analysis_data", None)


def overview():
    st.title("📊 학생 성적 탐색")
    st.write("학생의 배경 정보와 수학·읽기·쓰기 성적을 변수별로 비교하는 앱입니다.")
    show_metrics(st.session_state["analysis_data"])
    st.success("사이드바에서 분석할 변수를 선택하세요. 업로드한 파일과 학생 필터는 페이지를 이동해도 유지됩니다.")
    st.write("성별, 인종/배경, 부모 학력, 급식 유형, 시험 대비 과정 페이지에서 평균·중앙값·표준편차와 점수 분포를 비교할 수 있습니다.")
    st.write("과목 간 상관관계 페이지에서는 산점도와 회귀선, 상관계수 히트맵을 확인하고, 데이터 상세 조회에서 CSV를 다운로드할 수 있습니다.")


page = st.navigation({
    "시작": [st.Page(overview, title="데이터 업로드 및 개요", icon="📊", default=True)],
    "변수별 분석": [
        st.Page("analysis_pages/1_성별.py", title="성별", icon="👥"),
        st.Page("analysis_pages/2_인종_배경.py", title="인종/배경", icon="🌍"),
        st.Page("analysis_pages/3_부모_학력.py", title="부모 학력", icon="🎓"),
        st.Page("analysis_pages/4_급식_유형.py", title="급식 유형", icon="🍽️"),
        st.Page("analysis_pages/5_시험_대비_과정.py", title="시험 대비 과정", icon="📚"),
    ],
    "종합 탐색": [
        st.Page("analysis_pages/6_과목_간_상관관계.py", title="과목 간 상관관계", icon="🔎"),
        st.Page("analysis_pages/7_데이터_상세.py", title="데이터 상세 조회", icon="📋"),
    ],
})

# 모든 페이지에서 같은 업로더와 필터를 사용해 페이지 이동 시 값이 유지됩니다.
uploaded_file = st.sidebar.file_uploader(
    "학생 성적 CSV 업로드", type=["csv"], key="student_csv", on_change=change_file,
    help="본인이 가진 StudentsPerformance.csv 파일을 선택하세요. 파일 이름은 달라도 됩니다.",
)
st.session_state.pop("student_data", None)
st.session_state.pop("analysis_data", None)
if uploaded_file is None:
    st.title("📊 학생 성적 탐색")
    st.info("사이드바에서 CSV를 업로드하면 변수별 분석 페이지를 이용할 수 있습니다.")
    with st.expander("CSV 파일 형식 안내"):
        st.write("UTF-8 형식의 CSV에 다음 8개 열이 필요합니다. 과목 점수는 빈 값 없이 0~100 사이의 숫자여야 합니다.")
        st.code(",".join(list(FACTORS) + list(SCORES)), language="text")
    st.stop()

try:
    data = load_data(uploaded_file)
except UnicodeDecodeError:
    st.error("파일을 읽을 수 없습니다. UTF-8 형식의 CSV로 저장한 뒤 다시 업로드해주세요.")
    st.stop()
except pd.errors.EmptyDataError:
    st.error("파일이 비어 있습니다. 학생 데이터가 있는 CSV를 업로드해주세요.")
    st.stop()
except pd.errors.ParserError:
    st.error("CSV 형식이 올바르지 않습니다. 쉼표 구분과 각 행의 열 개수를 확인해주세요.")
    st.stop()
except ValueError as error:
    st.error(str(error))
    st.stop()

with st.sidebar:
    st.header("학생 필터")
    st.button("필터 초기화", on_click=reset_filters)
    filtered = data.copy()
    for column, label in FACTORS.items():
        options = sorted(data[column].unique())
        if column == "parental level of education":
            options = [value for value in EDUCATION_ORDER if value in options] + [
                value for value in options if value not in EDUCATION_ORDER
            ]
        selected = st.multiselect(label, options, default=options,
                                  format_func=lambda value: LABELS.get(value, value), key=f"filter_{column}")
        filtered = filtered[filtered[column].isin(selected)]
    low, high = st.slider("3개 과목 평균 점수 범위", 0, 100, (0, 100), key="score_range")
    filtered = filtered[filtered["평균 점수"].between(low, high)].copy()
    st.caption("점수 필터는 100점 만점인 세 과목의 산술평균에 적용됩니다.")
    st.write(f"선택 학생: **{len(filtered):,} / {len(data):,}명**")

st.session_state["student_data"] = data
st.session_state["analysis_data"] = filtered
if filtered.empty:
    st.warning("조건에 맞는 학생이 없습니다. 필터 선택이나 평균 점수 범위를 바꿔주세요.")
    st.stop()

st.caption("그룹 간 차이와 상관계수만으로 원인을 판단할 수 없습니다. 급식 유형은 경제적 배경을 직접 측정한 값이 아닙니다.")
page.run()
