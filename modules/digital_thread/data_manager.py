# modules/digital_thread/data_manager.py

def get_digital_thread_data():
    """
    조선 프로젝트의 주요 라이프사이클 데이터를 TAG 기반으로 매핑
    - Context: Spec -> POS(Purchase Order) -> Model -> Production 연계
    """
    
    # 공통 TAG: 'HULL-F10-PIPE-01' (이 태그로 모든 데이터가 동기화됨)
    digital_thread = [
        {
            "TAG": "H-F10-P01",
            "Spec (사양서)": "ASTM A106 Grade B (High-Temp Service)",
            "POS (구매)": "PO-2026-0042 (Supplier: SeAH Steel)",
            "Model (CAD)": "Pipe_Assembly_Fore_Block_10.step",
            "Production (생산)": "Spool Fabrication / Welding (Status: In-Progress)"
        },
        {
            "TAG": "H-F10-V02",
            "Spec (사양서)": "JIS B2002 (Gate Valve 10K)",
            "POS (구매)": "PO-2026-0115 (Supplier: KSB)",
            "Model (CAD)": "Valve_Gate_100A.step",
            "Production (생산)": "Installation (Status: Waiting)"
        }
    ]
    return digital_thread

def trace_by_tag(tag):
    """
    특정 태그를 추적하여 데이터 간의 관계(Digital Thread) 리포트 생성
    - 설계 변경 시 영향도 분석의 기초 로직
    """
    all_data = get_digital_thread_data()
    return [d for d in all_data if d["TAG"] == tag]