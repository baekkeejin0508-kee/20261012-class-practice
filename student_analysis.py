import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


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



def selected_data():
    data = st.session_state.get("analysis_data")
    if data is None:
        st.info("사이드바에서 학생 성적 CSV를 업로드해주세요.")
        st.stop()
    return data


def show_metrics(data):
    full_data = st.session_state["student_data"]
    cards = st.columns(5)
    cards[0].metric("전체 학생", f"{len(full_data):,}명")
    cards[1].metric("선택 학생", f"{len(data):,}명")
    for card, (column, label) in zip(cards[2:], SCORES.items()):
        card.metric(
            f"{label} 평균", f"{data[column].mean():.1f}점",
            f"{data[column].mean() - full_data[column].mean():+.1f}점", delta_color="off",
        )
    st.caption("과목별 지표는 선택 학생의 평균이며, 아래 차이는 전체 학생 평균 대비 점수 차이입니다.")


def render_factor(factor):
    data = selected_data()
    st.title(f"📊 {FACTORS[factor]}별 성적 비교")
    show_metrics(data)
    group_order = sorted(data[factor].unique())
    if factor == "parental level of education":
        group_order = [value for value in EDUCATION_ORDER if value in group_order] + [
            value for value in group_order if value not in EDUCATION_ORDER
        ]
    group_order = [LABELS.get(value, value) for value in group_order]
    long_data = data.melt(id_vars=[factor], value_vars=list(SCORES), var_name="과목", value_name="점수")
    long_data["과목"] = long_data["과목"].map(SCORES)
    long_data["그룹"] = long_data[factor].map(lambda value: LABELS.get(value, value))
    summary = long_data.groupby(["그룹", "과목"], as_index=False).agg(
        학생수=("점수", "size"), 평균=("점수", "mean"), 중앙값=("점수", "median"),
        표준편차=("점수", "std"), 최솟값=("점수", "min"), 최댓값=("점수", "max"),
    )
    st.subheader("과목별 평균 점수")
    means = px.bar(
        summary, x="그룹", y="평균", color="과목", barmode="group",
        category_orders={"그룹": group_order, "과목": list(SCORES.values())},
        labels={"그룹": FACTORS[factor], "평균": "평균 점수"},
        hover_data={"평균": ":.1f", "학생수": True, "중앙값": ":.1f"},
    )
    means.update_yaxes(range=[0, 100])
    st.plotly_chart(means, width="stretch", key=f"means_{factor}")

    subject = st.selectbox("분포를 볼 과목", list(SCORES.values()), key=f"subject_{factor}")
    subject_data = long_data[long_data["과목"] == subject]
    left, right = st.columns(2)
    with left:
        st.subheader(f"{subject} 점수 박스 플롯")
        box = px.box(subject_data, x="그룹", y="점수", color="그룹", points="outliers",
                     category_orders={"그룹": group_order}, labels={"그룹": FACTORS[factor]})
        box.update_yaxes(range=[0, 100])
        box.update_layout(showlegend=False)
        st.plotly_chart(box, width="stretch", key=f"box_{factor}")
    with right:
        st.subheader(f"{subject} 점수 분포")
        histogram = px.histogram(subject_data, x="점수", color="그룹", barmode="overlay", opacity=0.55,
                                 category_orders={"그룹": group_order}, labels={"그룹": FACTORS[factor]})
        histogram.update_traces(xbins={"start": 0, "end": 100, "size": 5})
        histogram.update_layout(xaxis_title="점수 (5점 구간)", yaxis_title="학생 수")
        st.plotly_chart(histogram, width="stretch", key=f"histogram_{factor}")
    st.caption("박스 가운데 선은 중앙값, 상자는 가운데 50%입니다. 바깥 점은 사분위 범위의 1.5배를 벗어난 관측값입니다. 히스토그램 높이는 그룹 인원의 영향을 받습니다.")
    st.subheader("그룹별 기술통계")
    st.dataframe(summary.round(2), hide_index=True, width="stretch")
    st.caption("표준편차는 점수의 퍼짐 정도입니다. 학생이 한 명인 그룹에서는 계산되지 않아 빈칸으로 표시됩니다.")


def render_correlations():
    data = selected_data()
    st.title("🔎 과목 간 상관관계")
    show_metrics(data)
    left, middle, right = st.columns(3)
    x_score = left.selectbox("가로축 과목", list(SCORES), index=1, format_func=SCORES.get)
    y_score = middle.selectbox("세로축 과목", list(SCORES), index=2, format_func=SCORES.get)
    color_factor = right.selectbox("색상 구분", list(FACTORS), format_func=FACTORS.get)
    scatter_data = data.copy()
    scatter_data["구분"] = scatter_data[color_factor].map(lambda value: LABELS.get(value, value))
    scatter = px.scatter(scatter_data, x=x_score, y=y_score, color="구분", opacity=0.6,
                         labels={**SCORES, "구분": FACTORS[color_factor]}, hover_data=list(SCORES))
    if len(data) >= 2 and data[x_score].nunique() > 1:
        # pandas로 최소제곱 회귀선을 계산해 추가 설치를 줄입니다.
        slope = data[x_score].cov(data[y_score]) / data[x_score].var()
        intercept = data[y_score].mean() - slope * data[x_score].mean()
        endpoints = [float(data[x_score].min()), float(data[x_score].max())]
        scatter.add_trace(go.Scatter(
            x=endpoints, y=[slope * value + intercept for value in endpoints],
            mode="lines", name="선택 학생 전체 회귀선", line={"color": "#333333", "dash": "dash"},
        ))
        st.caption("점선은 선택 학생 전체의 선형 회귀선입니다.")
    else:
        st.info("학생이 2명 이상이고 가로축 점수가 다양할 때 회귀선을 표시합니다.")
    scatter.update_xaxes(range=[0, 100])
    scatter.update_yaxes(range=[0, 100])
    st.plotly_chart(scatter, width="stretch", key="correlation_scatter")
    if x_score == y_score:
        st.caption("같은 과목을 선택했습니다. 과목 간 비교에는 서로 다른 과목을 선택하세요.")

    st.subheader("과목 간 피어슨 상관계수")
    correlations = data[list(SCORES)].rename(columns=SCORES).corr()
    if correlations.isna().all().all():
        st.info("학생 수가 부족하거나 점수가 모두 같아 상관계수를 계산할 수 없습니다.")
    else:
        heatmap = go.Figure(go.Heatmap(
            z=correlations.to_numpy().tolist(), x=list(correlations.columns), y=list(correlations.index),
            zmin=-1, zmax=1, colorscale="RdBu", colorbar={"title": "상관계수"},
            text=correlations.map(lambda value: "" if pd.isna(value) else f"{value:.2f}").to_numpy().tolist(),
            texttemplate="%{text}", hoverongaps=False,
            hovertemplate="%{y} · %{x}<br>상관계수: %{z:.3f}<extra></extra>",
        ))
        st.plotly_chart(heatmap, width="stretch", key="correlation_heatmap")
    st.dataframe(correlations.round(3), width="stretch")
    st.caption("상관계수는 -1부터 1까지이며, 1에 가까울수록 함께 증가하는 선형 관계가 강합니다. 계산할 수 없는 값은 빈칸으로 표시됩니다.")


def render_details():
    data = selected_data()
    st.title("📋 데이터 상세 조회")
    show_metrics(data)
    st.caption("필터를 적용한 데이터입니다. 원본 열 이름을 유지하고 세 과목 평균 점수를 추가했습니다.")
    st.dataframe(data, hide_index=True, width="stretch")
    st.download_button("선택 데이터 CSV 다운로드", data.to_csv(index=False).encode("utf-8-sig"),
                       file_name="StudentsPerformance_filtered.csv", mime="text/csv")
    st.subheader("과목별 기술통계")
    stats = data[list(SCORES)].rename(columns=SCORES).describe().rename(index={
        "count": "학생수", "mean": "평균", "std": "표준편차", "min": "최솟값",
        "25%": "1사분위수", "50%": "중앙값", "75%": "3사분위수", "max": "최댓값",
    })
    st.dataframe(stats.round(2), width="stretch")
