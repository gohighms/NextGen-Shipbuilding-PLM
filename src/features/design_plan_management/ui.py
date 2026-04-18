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
    top_col1, top_col2 = st.columns([1, 1])
    with top_col1:
        st.write(f"- 프로젝트: `{project_name}`")
        st.write("- 기준 일정 체계: `MDS → DP`")
    with top_col2:
        st.write(f"- MDS 작업 수: `{len(mds_rows)}`")
        st.write(f"- DP key event 수: `{len(dp_rows)}`")

    st.divider()
    st.subheader("1. MDS 기준 DP 수립 현황")
    st.info("차트는 현재 안정성 확인을 위해 잠시 비활성화했습니다.")
    st.caption("표준 설계 key event인 MDS를 기준으로, 현재 프로젝트 DP가 어떤 일정으로 수립되었는지 표로 확인할 수 있습니다.")

    overlay_table_rows = [
        {
            "설계 Key Event": row["설계 Key Event"],
            "기준 MDS": row["MDS 작업명"],
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

    st.markdown("#### DP key event와 모델 설계 연계")
    model_link_rows = [
        {
            "DP 번호": row["작업ID"],
            "설계 Key Event": row["설계 Key Event"],
            "작업 일자": f"{row['시작일']} ~ {row['종료일']}",
            "부서": row["부서"],
        }
        for row in dp_chart_rows
    ]
    st.dataframe(pd.DataFrame(model_link_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("2. 롤링 시뮬레이션")
    control_col1, control_col2 = st.columns([1, 1])
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
            value="선행 설계 검토 일정 변동에 따라 연계된 후속 설계계획을 함께 조정.",
        )
        st.write(f"- 선택 key event: `{selected_task_id}`")
        st.write(f"- 롤링 일수: `{shift_days}`일")

    rolled_rows = roll_dp_schedule(dp_rows, selected_task_id, shift_days)
    impact_summary = build_rolling_impact_summary(dp_rows, rolled_rows, selected_task_id, shift_days)
    rolled_chart_rows = build_schedule_chart_rows(rolled_rows, "롤링 후 DP")

    st.markdown("#### 롤링 후 DP")
    st.info("차트는 현재 안정성 확인을 위해 잠시 비활성화했습니다.")
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
            st.info("현재 설정에서는 이동된 후속 key event가 없습니다.")
