import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(page_title="학생 성적 탐색", page_icon="📊", layout="wide")

SCORES = {"math score": "수학", "reading score": "읽기", "writing score": "쓰기"}
FACTORS = {
    "gender": "성별",
    "race/ethnicity": "인종/배경 그룹",
    "parental level of education": "부모 학력",
    "lunch": "급식 유형",
    "test preparation course": "시험 대비 과정",
}
LABELS = {
    "female": "여학생", "male": "남학생",
    "standard": "일반 급식", "free/reduced": "지원 급식",
    "completed": "이수", "none": "미이수",
    "some high school": "고등학교 일부 이수", "high school": "고등학교 졸업",
    "some college": "대학 일부 이수", "associate's degree": "전문학사",
    "bachelor's degree": "학사", "master's degree": "석사",
}
EDUCATION_ORDER = [
    "some high school", "high school", "some college",
    "associate's degree", "bachelor's degree", "master's degree",
]


def load_data(uploaded_file):
    # 업로드한 파일만 읽고, 학생 데이터를 공용 캐시나 디스크에 저장하지 않습니다.
    uploaded_file.seek(0)
    data = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    data.columns = data.columns.str.strip()
    required_columns = list(FACTORS) + list(SCORES)
    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError("필수 열이 없습니다: " + ", ".join(missing))
    if data.empty:
        raise ValueError("학생 데이터가 없습니다. 헤더 아래에 학생 데이터가 있는 CSV를 업로드해주세요.")
    data = data[required_columns].copy()
    for column in FACTORS:
        if data[column].isna().any() or data[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"'{column}' 열에 빈 값이 있습니다. 값을 채운 뒤 다시 업로드해주세요.")
        data[column] = data[column].astype(str).str.strip()
    for column in SCORES:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if not data[column].between(0, 100).all():
            raise ValueError(f"'{column}' 열은 빈 값 없이 0~100 사이의 숫자여야 합니다.")
    data["평균 점수"] = data[list(SCORES)].mean(axis=1)
    return data


def reset_filters():
    for column in FACTORS:
        st.session_state.pop(f"filter_{column}", None)
    st.session_state.pop("score_range", None)


st.title("📊 학생 성적 탐색")
st.write("학생의 배경과 수학·읽기·쓰기 점수를 필터로 살펴보고 비교하세요.")

uploaded_file = st.sidebar.file_uploader(
    "학생 성적 CSV 업로드", type=["csv"], key="student_csv", on_change=reset_filters,
    help="본인이 가진 StudentsPerformance.csv 파일을 선택하세요. 파일 이름은 달라도 됩니다.",
)
if uploaded_file is None:
    st.info("학생 성적 CSV 파일을 사이드바에 업로드하면 분석 화면이 열립니다.")
    with st.expander("CSV 파일 형식 안내"):
        st.write("UTF-8 형식의 CSV에 다음 8개 열이 필요합니다. 각 과목 점수는 0~100 사이의 숫자여야 합니다.")
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

st.caption("차트는 선택한 학생들의 관측 결과입니다. 그룹 간 차이와 상관계수만으로 원인이나 개인의 능력을 판단할 수 없습니다. 급식 유형은 경제적 배경을 직접 측정한 값이 아닙니다.")

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
        selected = st.multiselect(
            label, options, default=options,
            format_func=lambda value: LABELS.get(value, value), key=f"filter_{column}",
        )
        filtered = filtered[filtered[column].isin(selected)]
    low, high = st.slider("3개 과목 평균 점수 범위", 0, 100, (0, 100), key="score_range")
    filtered = filtered[filtered["평균 점수"].between(low, high)].copy()
    st.caption("각 과목은 100점 만점입니다. 점수 필터는 세 과목의 산술평균에 적용됩니다.")
    st.divider()
    factor = st.selectbox(
        "비교 기준", list(FACTORS), index=4,
        format_func=lambda value: FACTORS[value], key="comparison_factor",
    )
    st.write(f"선택 학생: **{len(filtered):,} / {len(data):,}명**")

if filtered.empty:
    st.warning("조건에 맞는 학생이 없습니다. 필터 선택이나 평균 점수 범위를 바꿔주세요.")
    st.stop()

cards = st.columns(5)
cards[0].metric("전체 학생", f"{len(data):,}명")
cards[1].metric("선택 학생", f"{len(filtered):,}명")
for card, (column, label) in zip(cards[2:], SCORES.items()):
    card.metric(
        f"{label} 평균", f"{filtered[column].mean():.1f}점",
        f"{filtered[column].mean() - data[column].mean():+.1f}점", delta_color="off",
    )
st.caption("과목별 지표는 선택 학생의 평균이며, 아래 차이는 전체 학생 평균 대비 점수 차이입니다.")
st.write(f"선택 학생의 세 과목 평균: **{filtered['평균 점수'].mean():.1f}점** · 전체 학생: **{data['평균 점수'].mean():.1f}점**")

comparison_tab, correlation_tab, detail_tab = st.tabs([
    "배경 요인별 성적 비교", "과목 간 상관관계", "데이터 상세 조회",
])

with comparison_tab:
    st.subheader(f"{FACTORS[factor]}에 따른 과목별 평균과 분포")
    st.caption("사이드바의 비교 기준을 바꾸면 성별·인종/배경·부모 학력·급식 유형·시험 대비 과정별로 비교할 수 있습니다.")
    long_data = filtered.melt(id_vars=[factor], value_vars=list(SCORES), var_name="과목", value_name="점수")
    long_data["과목"] = long_data["과목"].map(SCORES)
    long_data["그룹"] = long_data[factor].map(lambda value: LABELS.get(value, value))
    group_order = [LABELS.get(value, value) for value in (
        EDUCATION_ORDER + sorted(set(filtered[factor]) - set(EDUCATION_ORDER))
        if factor == "parental level of education" else sorted(filtered[factor].unique())
    ) if value in filtered[factor].values]
    summary = long_data.groupby(["그룹", "과목"], as_index=False).agg(
        평균=("점수", "mean"), 중앙값=("점수", "median"), 학생수=("점수", "size"),
    )
    chart = alt.Chart(summary).mark_bar().encode(
        x=alt.X("그룹:N", sort=group_order, title=FACTORS[factor], axis=alt.Axis(labelAngle=-20)),
        xOffset=alt.XOffset("과목:N", sort=list(SCORES.values())),
        y=alt.Y("평균:Q", title="평균 점수", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("과목:N", sort=list(SCORES.values())),
        tooltip=["그룹:N", "과목:N", alt.Tooltip("평균:Q", format=".1f"), "학생수:Q"],
    ).properties(height=350)
    st.altair_chart(chart, width="stretch")
    subject = st.selectbox("분포를 볼 과목", list(SCORES.values()), key="distribution_subject")
    box = alt.Chart(long_data[long_data["과목"] == subject]).mark_boxplot(extent=1.5).encode(
        x=alt.X("그룹:N", sort=group_order, title=FACTORS[factor], axis=alt.Axis(labelAngle=-20)),
        y=alt.Y("점수:Q", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("그룹:N", legend=None),
    ).properties(height=300)
    st.altair_chart(box, width="stretch")
    st.caption("상자의 가운데 선은 중앙값, 상자는 가운데 50%의 점수입니다. 수염은 사분위 범위의 1.5배 이내이며, 바깥 점은 그 범위를 벗어난 관측값입니다.")
    st.dataframe(summary, hide_index=True, width="stretch")

    st.subheader("급식 유형별 평균 점수 분포")
    lunch_data = filtered[["lunch", "평균 점수"]].copy()
    lunch_data["급식 유형"] = lunch_data["lunch"].map(lambda value: LABELS.get(value, value))
    histogram = alt.Chart(lunch_data).mark_bar(opacity=0.55).encode(
        x=alt.X("평균 점수:Q", bin=alt.Bin(step=5, extent=[0, 100]), title="세 과목 평균 점수 (5점 구간)"),
        y=alt.Y("count():Q", stack=None, title="학생 수"),
        color="급식 유형:N",
        tooltip=["급식 유형:N", alt.Tooltip("count():Q", title="학생 수")],
    ).properties(height=280)
    st.altair_chart(histogram, width="stretch")
    lunch_summary = lunch_data.groupby("급식 유형").agg(학생수=("평균 점수", "size"), 평균점수=("평균 점수", "mean"))
    st.dataframe(lunch_summary.round(2), width="stretch")
    st.caption("히스토그램은 학생 수를 나타냅니다. 그룹의 전체 인원이 다르면 막대 높이도 영향을 받습니다.")

with correlation_tab:
    left, middle, right = st.columns(3)
    x_score = left.selectbox("가로축 과목", list(SCORES), index=1, format_func=SCORES.get)
    y_score = middle.selectbox("세로축 과목", list(SCORES), index=2, format_func=SCORES.get)
    color_factor = right.selectbox("색상 구분", list(FACTORS), format_func=FACTORS.get)
    scatter_data = filtered.copy()
    scatter_data["구분"] = scatter_data[color_factor].map(lambda value: LABELS.get(value, value))
    base = alt.Chart(scatter_data)
    points = base.mark_circle(size=55, opacity=0.5).encode(
        x=alt.X(f"{x_score}:Q", title=SCORES[x_score], scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f"{y_score}:Q", title=SCORES[y_score], scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("구분:N", title=FACTORS[color_factor]),
        tooltip=["구분:N"] + [alt.Tooltip(f"{column}:Q", title=label) for column, label in SCORES.items()],
    )
    if len(filtered) >= 2 and filtered[x_score].nunique() > 1:
        regression = base.transform_regression(x_score, y_score).mark_line(color="#333333", strokeDash=[6, 4]).encode(
            x=alt.X(f"{x_score}:Q"), y=alt.Y(f"{y_score}:Q"),
        )
        scatter = points + regression
        st.caption("점선은 선택 학생 전체의 선형 회귀선입니다. 점에 마우스를 올리면 점수를 볼 수 있습니다.")
    else:
        scatter = points
        st.info("학생이 2명 이상이고 가로축 점수가 다양할 때 회귀선을 표시합니다.")
    st.altair_chart(scatter.properties(height=400).interactive(), width="stretch")
    if x_score == y_score:
        st.caption("같은 과목을 선택했습니다. 과목 간 관계를 보려면 서로 다른 과목을 선택하세요.")

    st.subheader("과목 간 상관계수")
    correlations = filtered[list(SCORES)].rename(columns=SCORES).corr()
    heat_data = correlations.rename_axis("과목 1").reset_index().melt(
        id_vars="과목 1", var_name="과목 2", value_name="상관계수",
    )
    valid_heat_data = heat_data.dropna(subset=["상관계수"])
    if valid_heat_data.empty:
        st.info("학생 수가 부족하거나 점수가 모두 같아 상관계수를 계산할 수 없습니다.")
    else:
        heat_base = alt.Chart(valid_heat_data).encode(
            x=alt.X("과목 2:N", sort=list(SCORES.values()), axis=alt.Axis(labelAngle=0)),
            y=alt.Y("과목 1:N", sort=list(SCORES.values())),
        )
        heatmap = heat_base.mark_rect().encode(
            color=alt.Color("상관계수:Q", scale=alt.Scale(domain=[-1, 1], scheme="redblue")),
            tooltip=["과목 1:N", "과목 2:N", alt.Tooltip("상관계수:Q", format=".3f")],
        )
        labels = heat_base.mark_text(fontSize=18).encode(
            text=alt.Text("상관계수:Q", format=".2f"),
            color=alt.condition("abs(datum['상관계수']) > 0.6", alt.value("white"), alt.value("black")),
        )
        st.altair_chart((heatmap + labels).properties(height=300), width="stretch")
    st.dataframe(correlations.round(3), width="stretch")
    st.caption("피어슨 상관계수는 -1부터 1까지입니다. 1에 가까울수록 함께 증가하는 선형 관계가 강합니다. 계산할 수 없는 값은 빈칸으로 표시됩니다.")

with detail_tab:
    st.subheader(f"선택 학생 데이터 · {len(filtered):,}명")
    st.caption("원본의 영문 열 이름과 범주를 유지하고, 세 과목 평균 점수를 추가했습니다. 다운로드에는 현재 필터가 적용됩니다.")
    st.dataframe(filtered, hide_index=True, width="stretch")
    st.download_button(
        "선택 데이터 CSV 다운로드",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name="StudentsPerformance_filtered.csv", mime="text/csv",
    )
    st.subheader("과목별 기술통계")
    st.dataframe(filtered[list(SCORES)].rename(columns=SCORES).describe().round(2), width="stretch")
