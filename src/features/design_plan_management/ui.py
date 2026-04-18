import altair as alt
import pandas as pd
import streamlit as st

from src.common.reuse_state import get_current_spec
from src.features.design_plan_management.service import (
    build_dp_schedule,
    build_mds_schedule,
    build_overlay_rows,
    build_rolling_impact_summary,
    build_schedule_chart_rows,
    roll_dp_schedule,
)


def render_design_plan_management_page() -> None:
    current_spec = get_current_spec()
    project_name = current_spec["project_name"] if current_spec else "HD9001"

    st.title("설계계획(DP) 관리")
    st.caption("Master Design Schedule(MDS)를 기준으로 Design Plan(DP)을 수립하고, 롤링에 따라 연계된 설계계획이 함께 움직이는 시나리오를 보여줍니다.")

    mds_rows = build_mds_schedule(project_name)
    dp_rows = build_dp_schedule(project_name)
    mds_chart_rows = build_schedule_chart_rows(mds_rows, "MDS")
    dp_chart_rows = build_schedule_chart_rows(dp_rows, "DP")
    overlay_rows = build_overlay_rows(mds_rows, dp_rows)

    st.subheader("현재 연결 기준")
    top_col1, top_col2 = st.columns(2)
    with top_col1:
        st.write(f"- 프로젝트: `{project_name}`")
        st.write("- 기준 일정 체계: `MDS → DP`")
    with top_col2:
        st.write(f"- MDS key event 수: `{len(mds_rows)}`")
        st.write(f"- DP key event 수: `{len(dp_rows)}`")

    st.divider()
    st.subheader("1. MDS 기준 DP 수립 현황")
    st.caption("표준 설계 key event인 MDS를 기준으로, 현재 프로젝트의 DP가 어떤 일정으로 수립되었는지 보여줍니다.")

    overlay_chart_df = _build_overlay_chart_dataframe(mds_chart_rows, dp_chart_rows)
    st.altair_chart(_build_overlay_chart(overlay_chart_df), use_container_width=True)

    overlay_table_rows = [
        {
            "설계 Key Event": row["설계 Key Event"],
            "DP 번호": next(
                (item["작업ID"] for item in dp_chart_rows if item["설계 Key Event"] == row["설계 Key Event"]),
                "-",
            ),
            "DP 일정": f"{row['DP 시작일']} ~ {row['DP 종료일']}",
            "부서": row["부서"],
        }
        for row in overlay_rows
    ]
    st.dataframe(pd.DataFrame(overlay_table_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("2. 롤링 시뮬레이션")
    control_col1, control_col2 = st.columns(2)
    with control_col1:
        selected_task_id = st.selectbox(
            "롤링 대상 key event",
            options=[item["task_id"] for item in dp_rows],
            format_func=lambda task_id: next(
                f"{item['task_id']} / {item['key_event']}"
                for item in dp_rows
                if item["task_id"] == task_id
            ),
        )
        shift_days = st.slider("이동 일수", min_value=-7, max_value=14, value=5, step=1)
    with control_col2:
        rolling_reason = st.text_area(
            "롤링 사유",
            height=120,
            value="선행 설계 검토 일정 변경에 따라 연결된 후속 설계계획을 함께 조정.",
        )
        st.write(f"- 선택 key event: `{selected_task_id}`")
        st.write(f"- 롤링 일수: `{shift_days}`일")
        st.write(f"- 롤링 사유: `{rolling_reason}`")

    rolled_rows = roll_dp_schedule(dp_rows, selected_task_id, shift_days)
    impact_summary = build_rolling_impact_summary(dp_rows, rolled_rows, selected_task_id, shift_days)
    rolled_chart_rows = build_schedule_chart_rows(rolled_rows, "롤링 후 DP")

    st.markdown("#### 롤링 후 DP")
    rolled_chart_df = pd.DataFrame(rolled_chart_rows).copy()
    rolled_chart_df["강조"] = rolled_chart_df["작업ID"].apply(
        lambda value: "선택 key event" if value == selected_task_id else "연계 key event"
    )
    st.altair_chart(_build_rolled_chart(rolled_chart_df), use_container_width=True)

    rolled_table_rows = [
        {
            "DP 번호": row["작업ID"],
            "설계 Key Event": row["설계 Key Event"],
            "작업 일자": f"{row['시작일']} ~ {row['종료일']}",
            "부서": row["부서"],
            "연계 모델 설계": row["연계 모델 설계"],
        }
        for row in rolled_chart_rows
    ]
    st.dataframe(pd.DataFrame(rolled_table_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("3. 영향 요약")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("영향 받은 key event 수", impact_summary["changed_task_count"])
    metric_col2.metric("프로젝트 완료일 이동", f"{impact_summary['project_finish_shift_days']}일")
    metric_col3.metric("영향 부서 수", len(impact_summary["affected_departments"]))

    summary_col1, summary_col2 = st.columns([0.3, 0.7])
    with summary_col1:
        st.markdown("#### 영향 부서")
        if impact_summary["affected_departments"]:
            for department in impact_summary["affected_departments"]:
                st.write(f"- {department}")
        else:
            st.write("- 영향 없음")
    with summary_col2:
        st.markdown("#### 롤링 영향 상세")
        if impact_summary["changed_rows"]:
            st.dataframe(pd.DataFrame(impact_summary["changed_rows"]), use_container_width=True, hide_index=True)
        else:
            st.info("현재 설정에서는 이동되는 후속 key event가 없습니다.")


def _build_overlay_chart_dataframe(mds_chart_rows: list[dict], dp_chart_rows: list[dict]) -> pd.DataFrame:
    rows = []
    for item in mds_chart_rows:
        rows.append(
            {
                "설계 Key Event": item["설계 Key Event"],
                "시작일": item["시작일"],
                "종료일": item["종료일"],
                "계획구분": "MDS",
                "DP 번호": "",
            }
        )
    for item in dp_chart_rows:
        rows.append(
            {
                "설계 Key Event": item["설계 Key Event"],
                "시작일": item["시작일"],
                "종료일": item["종료일"],
                "계획구분": "DP",
                "DP 번호": item["작업ID"],
            }
        )
    return pd.DataFrame(rows)


def _build_overlay_chart(chart_df: pd.DataFrame) -> alt.Chart:
    color_scale = alt.Scale(domain=["MDS", "DP"], range=["#7c8aa5", "#d1495b"])
    event_order = chart_df["설계 Key Event"].drop_duplicates().tolist()

    bars = (
        alt.Chart(chart_df)
        .mark_bar(size=18, cornerRadius=4)
        .encode(
            x=alt.X("시작일:T", title="일정"),
            x2="종료일:T",
            y=alt.Y("설계 Key Event:N", sort=event_order, title="설계 Key Event"),
            color=alt.Color("계획구분:N", scale=color_scale, title="계획"),
            tooltip=["계획구분", "설계 Key Event", "시작일", "종료일", "DP 번호"],
            yOffset=alt.YOffset("계획구분:N"),
        )
    )

    labels = (
        alt.Chart(chart_df[chart_df["계획구분"] == "DP"])
        .mark_text(align="left", baseline="middle", dx=6, color="#d1495b", fontSize=11, fontWeight="bold")
        .encode(
            x="종료일:T",
            y=alt.Y("설계 Key Event:N", sort=event_order),
            text="DP 번호:N",
        )
    )

    return (bars + labels).properties(height=460)


def _build_rolled_chart(chart_df: pd.DataFrame) -> alt.Chart:
    color_scale = alt.Scale(domain=["선택 key event", "연계 key event"], range=["#d1495b", "#5c7cfa"])
    event_order = chart_df["설계 Key Event"].drop_duplicates().tolist()

    return (
        alt.Chart(chart_df)
        .mark_bar(size=18, cornerRadius=4)
        .encode(
            x=alt.X("시작일:T", title="일정"),
            x2="종료일:T",
            y=alt.Y("설계 Key Event:N", sort=event_order, title="설계 Key Event"),
            color=alt.Color("강조:N", scale=color_scale, title="구분"),
            tooltip=["작업ID", "설계 Key Event", "부서", "시작일", "종료일", "연계 모델 설계"],
        )
        .properties(height=460)
    )
