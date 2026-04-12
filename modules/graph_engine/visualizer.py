from pyvis.network import Network
import streamlit.components.v1 as components
import os

def generate_knowledge_graph(data):
    """
    Digital Thread 데이터를 지식 그래프(Knowledge Graph)로 변환
    - Description: 
        TAG를 중심으로 Spec, POS, Model, Production 간의 관계를 노드화함.
        상향식/하향식 데이터 추적성을 시각적으로 증명하기 위한 모듈.
    """
    # 그래프 초기화 (밝은 배경, 물리 엔진 활성화)
    net = Network(height="500px", width="100%", bgcolor="#ffffff", font_color="black", directed=True)
    
    for item in data:
        tag = item["TAG"]
        
        # 1. 중심 노드 (TAG)
        net.add_node(tag, label=tag, color="#eb4034", size=25, title=f"Central Tag: {tag}")
        
        # 2. 관계 노드 생성 및 연결 (Spec, POS, Model, Production)
        nodes = [
            ("Spec", item["Spec (사양서)"], "#4287f5"),
            ("POS", item["POS (구매)"], "#42f59e"),
            ("Model", item["Model (CAD)"], "#f5a442"),
            ("Prod", item["Production (생산)"], "#a142f5")
        ]
        
        for category, label, color in nodes:
            node_id = f"{tag}_{category}"
            net.add_node(node_id, label=label[:15] + "...", title=label, color=color, size=15)
            net.add_edge(tag, node_id, label=category)

    # 물리 엔진 설정 (노드들이 겹치지 않게 퍼지는 효과)
    net.toggle_physics(True)
    
    # 임시 HTML 파일 저장 및 로드
    path = "graph_temp.html"
    net.save_graph(path)
    
    with open(path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return html_content