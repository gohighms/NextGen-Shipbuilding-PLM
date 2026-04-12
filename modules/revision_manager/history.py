# modules/revision_manager/history.py

def get_revision_history():
    """
    특정 아이템의 리비전 히스토리 데이터를 관리
    - Description: 
        변경 사유(Reason for Change)와 일시, 담당자를 기록하여 추적성을 확보.
    """
    # 시나리오: 선급 지적 사항(Comment) 대응을 위한 리비전 업그레이드
    history = [
        {
            "Revision": "P01",
            "Date": "2026-03-01",
            "Author": "Minseok Ko",
            "Status": "Released",
            "Change_Log": "Initial Release for Approval"
        },
        {
            "Revision": "P02",
            "Date": "2026-04-10",
            "Author": "Minseok Ko",
            "Status": "Released",
            "Change_Log": "Reflected Class Comment (Thickness increased from 10t to 12t)"
        },
        {
            "Revision": "P03",
            "Date": "2026-04-12",
            "Author": "Minseok Ko",
            "Status": "In-Work",
            "Change_Log": "Updated due to Production feedback (Welding sequence optimization)"
        }
    ]
    return history