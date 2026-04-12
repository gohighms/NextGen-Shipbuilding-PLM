# apps/main_app.py
import streamlit as st
import streamlit.components.v1 as components
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from modules.cad_engine.parser import extract_bom_from_step
from modules.digital_thread.data_manager import get_digital_thread_data
from modules.graph_engine.visualizer import generate_knowledge_graph
from modules.revision_manager.history import get_revision_history

# 페이지 대시보드 설정
st.set_page_config(page_title="NexGen Ship PLM", layout="wide")

st.title("🚢 Next-Gen Shipbuilding PLM Platform")

# 사이드바 메뉴
st.sidebar.header("Control Panel")
menu = st.sidebar.radio("Navigation", ["Visual BOM Engine", "Digital Thread", "Knowledge Graph", "Revision Manager"])

if menu == "Visual BOM Engine":
    st.subheader("BOM Extraction from CAD Data")
    
    # 파일 업로드
    uploaded_file = st.file_uploader("Upload STEP File (.stp / .step)", type=["stp", "step"])
    
    # 파서 호출하여 데이터 가져오기
    bom_list = extract_bom_from_step(uploaded_file)
    
    # 화면 분할 (BOM 리스트 / 3D 뷰어 예비)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("### 📂 Engineering BOM")
        # 표 형식으로 출력
        st.table(bom_list)
        
    with col2:
        st.write("### 🎨 Visual Preview")
        st.info("3D 렌더링 모듈 준비 중입니다.")

elif menu == "Digital Thread":
    st.header("🔗 Digital Thread Mapper")
    st.markdown("##### 통합 데이터 흐름: Spec ➔ Purchase ➔ Design ➔ Production")
    
    # 데이터 로드
    thread_data = get_digital_thread_data()
    
    # 1. 시각적인 Flow 차트 (Streamlit의 간단한 단계 표시 활용)
    st.write("### 🏗️ Thread Continuity Status")
    for item in thread_data:
        with st.expander(f"TAG: {item['TAG']} - Lifecycle Trace"):
            cols = st.columns(4)
            cols[0].metric("1. Spec", "Verified")
            cols[1].metric("2. Purchase", "Ordered")
            cols[2].metric("3. Design", "Released")
            cols[3].metric("4. Production", "In-Progress")
            
            st.json(item) # 실제 데이터 상세 확인

    # 2. 통합 관리 테이블
    st.write("### 📊 Master Thread Table")
    st.dataframe(thread_data, use_container_width=True)

elif menu == "Knowledge Graph":
    st.header("🧠 Knowledge Graph & Semantic Search")
    st.write("TAG 기반 온톨로지 시각화 및 데이터 간 관계 분석")
    
    # Digital Thread 데이터 가져오기
    thread_data = get_digital_thread_data()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("### 🌐 Semantic Network View")
        # 그래프 생성 및 렌더링
        graph_html = generate_knowledge_graph(thread_data)
        components.html(graph_html, height=550)
        
    with col2:
        st.write("### 🔍 AI Insights (RAG)")
        st.text_input("질문을 입력하세요 (예: 특정 태그의 선급 규칙은?)")
        st.info("LLM 연동을 통해 그래프 내 데이터를 기반으로 답변을 생성합니다.")
        
        st.write("#### 연관 데이터")
        st.caption("- Class Rule: DNV-RU-SHIP Pt.3")
        st.caption("- Material Cert: EN 10204 3.1")

elif menu == "Revision Manager":
    st.header("📑 Intelligent Revision Manager")
    st.write("아이템별 설계 변경 이력 및 리비전 제어")
    
    # 리비전 데이터 로드
    rev_history = get_revision_history()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("### 🔍 Item Selection")
        selected_item = st.selectbox("대상 아이템 선택", ["H-F10-P01 (Ballast Pipe)", "H-F10-V02 (Gate Valve)"])
        st.info(f"선택된 아이템: {selected_item}")
        
        # 현재 상태 표시
        st.success("Current Status: Released (Rev.P02)")
        
    with col2:
        st.write("### 📜 Change Log History")
        
        # 타임라인 스타일로 히스토리 표시
        for rev in reversed(rev_history):
            with st.container():
                st.markdown(f"**Revision: {rev['Revision']}** ({rev['Date']})")
                st.write(f"- **Author:** {rev['Author']}")
                st.write(f"- **Description:** {rev['Change_Log']}")
                st.divider()

    # 리비전 비교 기능 (가상)
    st.write("### 🔄 Revision Comparison")
    c1, c2 = st.columns(2)
    c1.json(rev_history[0]) # Rev.P01
    c2.json(rev_history[1]) # Rev.P02