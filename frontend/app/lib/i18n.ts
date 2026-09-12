// 다국어 메시지 사전과 언어 유틸리티를 담당하는 파일
export const languages = ["ko", "en", "vi"] as const;
export type Language = (typeof languages)[number];

export function getLanguage(value?: string): Language {
  return languages.includes(value as Language) ? value as Language : "ko";
}

export function localized(value: Record<string, string>, language: Language): string {
  return value[language] || value.ko || Object.values(value)[0] || "";
}

export function localizedList(value: Record<string, string[]>, language: Language): string[] {
  return value[language] || value.ko || Object.values(value)[0] || [];
}

export function withLanguage(path: string, language: Language): string {
  const separator = path.includes("?") ? "&" : "?";
  return language === "ko" ? path : `${path}${separator}lang=${language}`;
}

export const messages = {
  ko: {
    navGuides: "상황별 가이드", heroTitle: "낯선 전북 생활을", heroEmphasis: "하나로 잇다",
    heroDescription: "체류·행정과 노동 문제를 모국어로 질문하고,\n공식정보에 근거한 안내와 지원기관을 확인하세요.", askAi: "AI에게 질문하기", viewGuides: "상황별 가이드 보기",
    trust: "✓ 공식정보 기반   ✓ 답변 출처 제공   ✓ 개인정보 보호", guideTitle: "상황별 가이드", guideDescription: "지금 겪고 있는 상황을 선택하면 필요한 절차와 서류를 순서대로 알려드려요.", ragSearching: "공식 자료를 검색하고 있어요…", rag: "공식 문서 기반 안내", insufficient: "확인된 공식 자료만으로 답변하기 어렵습니다.", sourceDocuments: "답변에 사용한 공식 자료", verifiedOn: "정보 확인일", evidenceNote: "이 안내는 검색된 공식 자료 범위에 한정됩니다.", fallbackNotice: "AI 공식자료 검색 답변이 아닌 기본 안내입니다.", followUp: "추가로 확인할 사항", noSources: "공식 자료 출처가 없습니다.",
    all: "전체", residency: "체류·행정", labor: "노동", found: "개의 가이드를 찾았어요.", documents: "준비서류", detail: "자세히 보기 →", back: "← 가이드 목록",
    steps: "진행 순서", caution: "꼭 확인하세요", help: "도움을 받을 곳", website: "웹사이트 ↗", source: "공식 출처", verified: "정보 확인일", chatTitle: "AI 상담 챗봇", chatDescription: "체류·행정 또는 노동 문제를 편하게 적어주세요.", chatPlaceholder: "예: 회사에서 두 달째 월급을 받지 못했어요.", send: "가이드 찾기", result: "상담 결과", relatedGuide: "관련 가이드", askAnother: "다시 질문하기", noPersonal: "여권번호, 외국인등록번호 등 개인정보는 입력하지 마세요.", aiAnswer: "AI 맞춤 안내", rulesAnswer: "기본 가이드 안내", feedbackQuestion: "이 안내가 도움이 되었나요?", helpful: "도움이 됐어요", notHelpful: "부족해요", feedbackThanks: "의견을 보내주셔서 감사합니다.", cachedAnswer: "빠른 결과",
  },
  en: {
    navGuides: "Situation guides", heroTitle: "Make life in Jeonbuk", heroEmphasis: "feel connected",
    heroDescription: "Ask about immigration and labor issues in your language.\nGet guidance based on official information and find support.", askAi: "Ask AI", viewGuides: "View situation guides",
    trust: "✓ Official sources   ✓ Sources provided   ✓ Privacy protected", guideTitle: "Situation guides", guideDescription: "Choose your situation to see the required steps and documents.", ragSearching: "Searching official materials…", rag: "Official document-based guidance", insufficient: "We cannot answer reliably from the verified official materials found.", sourceDocuments: "Official sources used", verifiedOn: "Verified on", evidenceNote: "This guidance is limited to the official materials retrieved.", fallbackNotice: "This is basic guidance, not an AI answer based on retrieved official materials.", followUp: "Please also check", noSources: "No official source was retrieved.",
    all: "All", residency: "Stay & administration", labor: "Labor", found: "guides found.", documents: "Documents", detail: "View details →", back: "← All guides",
    steps: "What to do", caution: "Please note", help: "Where to get help", website: "Website ↗", source: "Official source", verified: "Verified on", chatTitle: "AI Consultation Chatbot", chatDescription: "Describe your immigration, administration, or labor issue.", chatPlaceholder: "Example: I have not been paid for two months.", send: "Find guidance", result: "Consultation result", relatedGuide: "Related guide", askAnother: "Ask another question", noPersonal: "Do not enter passport numbers, residence card numbers, or other personal data.", aiAnswer: "Personalized AI guidance", rulesAnswer: "Standard guide result", feedbackQuestion: "Was this guidance helpful?", helpful: "Helpful", notHelpful: "Needs improvement", feedbackThanks: "Thank you for your feedback.", cachedAnswer: "Fast result",
  },
  vi: {
    navGuides: "Hướng dẫn theo tình huống", heroTitle: "Kết nối cuộc sống", heroEmphasis: "tại Jeonbuk",
    heroDescription: "Hỏi về cư trú và lao động bằng ngôn ngữ của bạn.\nXem hướng dẫn chính thức và tìm cơ quan hỗ trợ.", askAi: "Hỏi AI", viewGuides: "Xem hướng dẫn",
    trust: "✓ Nguồn chính thức   ✓ Có nguồn tham khảo   ✓ Bảo vệ riêng tư", guideTitle: "Hướng dẫn theo tình huống", guideDescription: "Chọn tình huống để xem các bước và giấy tờ cần thiết.", ragSearching: "Đang tìm tài liệu chính thức…", rag: "Hướng dẫn dựa trên tài liệu chính thức", insufficient: "Chưa thể trả lời đáng tin cậy từ tài liệu chính thức đã tìm thấy.", sourceDocuments: "Nguồn chính thức đã dùng", verifiedOn: "Ngày xác minh", evidenceNote: "Hướng dẫn này chỉ dựa trên tài liệu chính thức đã tìm được.", fallbackNotice: "Đây là hướng dẫn cơ bản, không phải câu trả lời AI dựa trên tài liệu đã tìm.", followUp: "Nội dung cần kiểm tra thêm", noSources: "Không tìm thấy nguồn chính thức.",
    all: "Tất cả", residency: "Cư trú & hành chính", labor: "Lao động", found: "hướng dẫn được tìm thấy.", documents: "Giấy tờ", detail: "Xem chi tiết →", back: "← Danh sách hướng dẫn",
    steps: "Các bước thực hiện", caution: "Điều cần lưu ý", help: "Nơi hỗ trợ", website: "Trang web ↗", source: "Nguồn chính thức", verified: "Ngày xác minh", chatTitle: "Chatbot tư vấn AI", chatDescription: "Hãy mô tả vấn đề cư trú, hành chính hoặc lao động.", chatPlaceholder: "Ví dụ: Tôi chưa được trả lương trong hai tháng.", send: "Tìm hướng dẫn", result: "Kết quả tư vấn", relatedGuide: "Hướng dẫn liên quan", askAnother: "Đặt câu hỏi khác", noPersonal: "Không nhập số hộ chiếu, số thẻ cư trú hoặc dữ liệu cá nhân.", aiAnswer: "Hướng dẫn AI cá nhân hóa", rulesAnswer: "Hướng dẫn cơ bản", feedbackQuestion: "Hướng dẫn này có hữu ích không?", helpful: "Hữu ích", notHelpful: "Cần cải thiện", feedbackThanks: "Cảm ơn ý kiến của bạn.", cachedAnswer: "Kết quả nhanh",
  },
} as const;

export const featureMessages = {
  ko: [["AI 상담", "모국어로 생활과 노동 문제를 질문하세요."], ["상황별 가이드", "체류·행정 및 노동 절차를 단계별로 확인하세요."], ["문서 설명", "어려운 한국어 문서를 쉬운 말로 이해하세요."], ["기관 찾기", "내 상황과 위치에 맞는 지원기관을 찾아보세요."]],
  en: [["AI consultation", "Ask about daily life and labor issues in your language."], ["Situation guides", "Follow immigration and labor procedures step by step."], ["Document help", "Understand difficult Korean documents in plain language."], ["Find support", "Find an agency suited to your situation and location."]],
  vi: [["Tư vấn AI", "Hỏi về đời sống và lao động bằng ngôn ngữ của bạn."], ["Hướng dẫn", "Xem từng bước thủ tục cư trú và lao động."], ["Giải thích tài liệu", "Hiểu tài liệu tiếng Hàn bằng lời dễ hiểu."], ["Tìm cơ quan", "Tìm cơ quan phù hợp với tình huống và vị trí của bạn."]],
} as const;
