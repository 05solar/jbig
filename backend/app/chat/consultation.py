# 언어 감지와 키워드 규칙 기반 가이드 매칭(규칙 상담 계층)을 담당하는 파일
import re

from ..data.seed import AGENCIES, GUIDES
from ..core.schemas import Agency, ConsultationResponse, Guide, Language


KEYWORDS = {
    "alien-registration": ["외국인등록", "등록증 처음", "alien registration", "register as a foreign", "đăng ký người nước ngoài"],
    "stay-extension": ["체류기간", "연장", "만료", "extension", "expire", "overstay", "gia hạn", "hết hạn"],
    "change-of-address": ["체류지", "주소 변경", "이사", "address", "moved", "moving", "địa chỉ", "chuyển nhà"],
    "registration-card-reissue": ["등록증 분실", "등록증 재발급", "카드 분실", "잃어버렸", "분실했", "lost card", "reissue", "mất thẻ", "cấp lại thẻ"],
    "status-change": ["체류자격 변경", "비자 변경", "change visa", "change of status", "đổi visa", "thay đổi tư cách"],
    "unpaid-wages": ["임금체불", "월급 안", "월급을 안", "월급 못", "월급을 못", "급여 안", "급여를 안", "돈을 못", "못 받", "unpaid", "not paid", "wage", "salary", "nợ lương", "chưa trả lương"],
    "missing-contract": ["계약서 없", "계약서 안", "계약서를 안", "안 써줘", "미작성", "no contract", "without contract", "không có hợp đồng"],
    "minimum-wage": ["최저임금", "시급", "minimum wage", "hourly pay", "lương tối thiểu", "lương theo giờ"],
    "sudden-dismissal": [
        "해고", "잘렸", "나오지 말", "나오지마", "그만 나오", "출근하지 말", "출근하지마",
        "내일부터 나오", "더 이상 나오", "dismiss", "fired", "termination", "do not come to work",
        "don't come to work", "stop coming to work", "sa thải", "đuổi việc", "đừng đi làm",
        "không cần đi làm", "nghỉ việc từ ngày mai",
    ],
    "industrial-accident": ["산재", "일하다 다", "작업 중 사고", "work accident", "injured at work", "industrial accident", "tai nạn lao động", "bị thương khi làm"],
    "working-hours-overtime": ["근로시간", "연장근로", "야근", "초과근무", "오래 일", "overtime", "working hours", "too many hours", "làm thêm giờ", "tăng ca"],
    "holiday-work": ["휴일", "주휴", "holiday work", "work on holiday", "ngày nghỉ"],
    "annual-leave": ["연차", "annual leave", "nghỉ phép"],
}

MESSAGES = {
    "ko": ("질문과 가장 관련 있는 가이드를 찾았습니다. 아래 절차와 기관 정보를 확인하세요.", "정확히 일치하는 가이드를 찾지 못했습니다. 1345 또는 1350에 상담해 주세요."),
    "en": ("I found the guide most relevant to your question. Review the steps and support contacts below.", "I could not find an exact guide. Please contact 1345 or 1350 for help."),
    "vi": ("Đã tìm thấy hướng dẫn phù hợp nhất với câu hỏi. Hãy xem các bước và nơi hỗ trợ bên dưới.", "Không tìm thấy hướng dẫn phù hợp chính xác. Vui lòng gọi 1345 hoặc 1350."),
}

URGENT = {
    "ko": "생명이 위험하거나 크게 다쳤다면 서류 준비보다 먼저 119에 연락하세요.",
    "en": "If someone is seriously injured or in danger, call 119 before handling paperwork.",
    "vi": "Nếu có người bị thương nặng hoặc nguy hiểm đến tính mạng, hãy gọi 119 trước khi làm giấy tờ.",
}


def detect_language(text: str) -> Language:
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[ăâđêôơưĂÂĐÊÔƠƯ]|[àáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", text):
        return "vi"
    return "en"


def find_guides(question: str, limit: int = 3) -> list[Guide]:
    normalized = question.casefold()
    scores = {guide_id: sum(2 if " " in keyword else 1 for keyword in keywords if keyword.casefold() in normalized) for guide_id, keywords in KEYWORDS.items()}
    ranked_ids = [guide_id for guide_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score > 0][:limit]
    guides = [guide for guide_id in ranked_ids for guide in GUIDES if guide.id == guide_id]
    return sorted(guides, key=lambda guide: guide.id != "industrial-accident")


def find_guide(question: str) -> Guide | None:
    guides = find_guides(question, limit=1)
    return guides[0] if guides else None


def build_consultation(guides: list[Guide], language: Language) -> ConsultationResponse:
    if not guides:
        return ConsultationResponse(language=language, message=MESSAGES[language][1], guide=None, guides=[], agencies=[], urgent_notice=None)
    agency_ids = {agency_id for guide in guides for agency_id in guide.agency_ids}
    agencies: list[Agency] = [agency for agency in AGENCIES if agency.id in agency_ids]
    urgent_notice = URGENT[language] if any(guide.id == "industrial-accident" for guide in guides) else None
    categories = list(dict.fromkeys(guide.category for guide in guides))
    intents = list(dict.fromkeys(guide.id for guide in guides))
    return ConsultationResponse(language=language, message=MESSAGES[language][0], guide=guides[0], guides=guides, agencies=agencies, urgent_notice=urgent_notice, categories=categories, intents=intents)


def consult(question: str, requested_language: Language | None = None) -> ConsultationResponse:
    language = requested_language or detect_language(question)
    return build_consultation(find_guides(question), language)
