# 가이드 13종과 지원기관 5곳의 시드 데이터(3개 언어)를 정의하는 파일
from ..core.schemas import Agency, Guide


AGENCIES = [
    Agency(id="immigration", name={"ko": "전주출입국·외국인사무소", "en": "Jeonju Immigration Office", "vi": "Văn phòng Xuất nhập cảnh Jeonju"}, description={"ko": "체류, 등록, 비자 관련 민원을 처리합니다.", "en": "Handles stay, registration, and visa services.", "vi": "Xử lý thủ tục cư trú, đăng ký và thị thực."}, phone="1345", website="https://www.immigration.go.kr/", address="전북특별자치도 전주시 덕진구 동부대로 857"),
    Agency(id="hikorea", name={"ko": "하이코리아", "en": "Hi Korea", "vi": "Hi Korea"}, description={"ko": "외국인 전자민원과 체류 정보를 제공합니다.", "en": "Provides online immigration services.", "vi": "Cung cấp dịch vụ nhập cư trực tuyến."}, phone="1345", website="https://www.hikorea.go.kr/", address="온라인 서비스"),
    Agency(id="labor-office", name={"ko": "고용노동부 전주지청", "en": "Jeonju Labor Office", "vi": "Văn phòng Lao động Jeonju"}, description={"ko": "임금, 해고, 근로조건 관련 상담과 신고를 지원합니다.", "en": "Supports labor consultations and complaints.", "vi": "Hỗ trợ tư vấn và khiếu nại lao động."}, phone="1350", website="https://www.moel.go.kr/", address="전북특별자치도 전주시 덕진구 건산로 251"),
    Agency(id="workers-comp", name={"ko": "근로복지공단", "en": "Workers' Compensation Service", "vi": "Cơ quan Bồi thường Lao động"}, description={"ko": "산재보험 신청과 보상 절차를 안내합니다.", "en": "Guides workers' compensation claims.", "vi": "Hướng dẫn bồi thường tai nạn lao động."}, phone="1588-0075", website="https://www.comwel.or.kr/", address="전북지역 관할 지사"),
    Agency(id="danuri", name={"ko": "다누리콜센터", "en": "Danuri Helpline", "vi": "Tổng đài Danuri"}, description={"ko": "15개 언어로 생활정보와 통역 상담을 제공합니다.", "en": "Provides multilingual information and interpretation.", "vi": "Cung cấp thông tin và phiên dịch đa ngôn ngữ."}, phone="1577-1366", website="https://www.liveinkorea.kr/", address="전화·온라인 상담"),
]

AGENCY_DETAILS = {
    "immigration": {"region": "jeonju", "service_types": ["immigration", "administration"], "supported_languages": ["ko", "en", "vi"], "hours": {"ko": "평일 09:00~18:00 · 방문 전 예약·공휴일 확인", "en": "Weekdays 09:00–18:00 · Check reservations and holidays", "vi": "Ngày thường 09:00–18:00 · Kiểm tra lịch hẹn và ngày nghỉ"}, "latitude": 35.8506, "longitude": 127.1578},
    "hikorea": {"region": "online", "service_types": ["immigration", "administration", "online"], "supported_languages": ["ko", "en", "vi"], "hours": {"ko": "온라인 서비스", "en": "Online service", "vi": "Dịch vụ trực tuyến"}},
    "labor-office": {"region": "jeonju", "service_types": ["labor", "wages", "dismissal"], "supported_languages": ["ko"], "hours": {"ko": "평일 운영 · 방문 전 1350 확인", "en": "Weekdays · Call 1350 before visiting", "vi": "Ngày thường · Gọi 1350 trước khi đến"}, "latitude": 35.8355, "longitude": 127.1465},
    "workers-comp": {"region": "jeonbuk", "service_types": ["labor", "industrial_accident"], "supported_languages": ["ko"], "hours": {"ko": "평일 운영 · 방문 전 1588-0075 확인", "en": "Weekdays · Call 1588-0075 before visiting", "vi": "Ngày thường · Gọi 1588-0075 trước khi đến"}},
    "danuri": {"region": "phone", "service_types": ["interpretation", "living", "emergency", "labor", "immigration"], "supported_languages": ["ko", "en", "vi", "zh", "tl", "km", "mn", "ru", "ja", "th", "lo", "uz", "ne", "ar", "id"], "hours": {"ko": "365일 24시간", "en": "24 hours, 365 days", "vi": "24 giờ, 365 ngày"}, "emergency": True},
}
AGENCIES = [agency.model_copy(update=AGENCY_DETAILS[agency.id]) for agency in AGENCIES]


TRANSLATIONS = {
    "alien-registration": {
        "en": ("Register as a foreign resident when staying in Korea long-term.", ["Check the registration deadline and immigration office.", "Book a visit and submit the required documents.", "Collect your residence card after review."], ["Passport", "Application form", "Proof of residence", "Documents for your visa status", "Fee"], ["Additional documents differ by visa status.", "Do not miss the legal reporting deadline."]),
        "vi": ("Đăng ký người nước ngoài khi cư trú dài hạn tại Hàn Quốc.", ["Kiểm tra hạn đăng ký và cơ quan xuất nhập cảnh phụ trách.", "Đặt lịch và nộp giấy tờ cần thiết.", "Nhận thẻ cư trú sau khi xét duyệt."], ["Hộ chiếu", "Đơn đăng ký tổng hợp", "Giấy tờ chứng minh nơi ở", "Giấy tờ theo tư cách lưu trú", "Lệ phí"], ["Giấy tờ bổ sung khác nhau tùy tư cách lưu trú.", "Không để quá hạn khai báo theo luật."]),
    },
    "stay-extension": {
        "en": ("Apply for an extension before your authorized stay expires.", ["Check the expiration date on your residence card.", "Check whether you can apply online or must visit.", "Submit the documents and fee before the deadline."], ["Passport", "Residence card", "Application form", "Documents supporting your visa status"], ["Overstaying may result in penalties.", "Some visa statuses cannot apply online."]),
        "vi": ("Xin gia hạn trước khi thời gian cư trú hết hạn.", ["Kiểm tra ngày hết hạn trên thẻ cư trú.", "Kiểm tra có thể đăng ký trực tuyến hay phải đến trực tiếp.", "Nộp giấy tờ và lệ phí trước hạn."], ["Hộ chiếu", "Thẻ cư trú", "Đơn đăng ký tổng hợp", "Giấy tờ chứng minh tư cách lưu trú"], ["Quá hạn cư trú có thể bị xử phạt.", "Một số tư cách lưu trú không thể đăng ký trực tuyến."]),
    },
    "change-of-address": {
        "en": ("Report your new place of residence after moving.", ["Prepare proof of your new address.", "Check whether to report at a local office, immigration office, or online.", "Confirm that the report was accepted."], ["Passport", "Residence card", "Proof of residence", "Application form"], ["Count the reporting deadline from your moving date.", "You must be able to prove your actual residence."]),
        "vi": ("Khai báo nơi cư trú mới sau khi chuyển nhà.", ["Chuẩn bị giấy tờ chứng minh địa chỉ mới.", "Kiểm tra khai báo tại văn phòng địa phương, xuất nhập cảnh hay trực tuyến.", "Xác nhận khai báo đã được tiếp nhận."], ["Hộ chiếu", "Thẻ cư trú", "Giấy tờ chứng minh nơi ở", "Đơn đăng ký tổng hợp"], ["Tính hạn khai báo từ ngày chuyển nhà.", "Phải chứng minh được nơi ở thực tế."]),
    },
    "registration-card-reissue": {
        "en": ("Have a lost or damaged residence card reissued.", ["Check the reason and requirements for reissue.", "Book a visit and apply at the immigration office.", "Keep the receipt and collect the new card."], ["Passport", "Application form", "Photo", "Proof of the reason for reissue", "Fee"], ["Apply within the required period if the card was lost.", "Check the photo specifications in advance."]),
        "vi": ("Cấp lại thẻ cư trú bị mất hoặc hư hỏng.", ["Kiểm tra lý do và điều kiện cấp lại.", "Đặt lịch và nộp đơn tại cơ quan xuất nhập cảnh.", "Giữ giấy tiếp nhận và nhận thẻ mới."], ["Hộ chiếu", "Đơn đăng ký tổng hợp", "Ảnh", "Giấy tờ về lý do cấp lại", "Lệ phí"], ["Nếu mất thẻ, hãy đăng ký trong thời hạn quy định.", "Kiểm tra trước quy cách ảnh."]),
    },
    "status-change": {
        "en": ("Change your visa status when your purpose changes, such as study or work.", ["Check the eligibility and permitted activities for the new status.", "Prepare and submit all status-specific documents.", "Follow the limits of your current status until approval."], ["Passport", "Residence card", "Application form", "Documents supporting the status change", "Fee"], ["Check whether approval is required before starting a new activity.", "Decisions vary depending on individual circumstances."]),
        "vi": ("Thay đổi tư cách lưu trú khi mục đích như học tập hoặc làm việc thay đổi.", ["Kiểm tra điều kiện và hoạt động được phép của tư cách mới.", "Chuẩn bị và nộp giấy tờ theo từng tư cách.", "Tuân thủ phạm vi tư cách hiện tại cho đến khi được phép."], ["Hộ chiếu", "Thẻ cư trú", "Đơn đăng ký tổng hợp", "Giấy tờ chứng minh thay đổi tư cách", "Lệ phí"], ["Kiểm tra có cần được phép trước khi bắt đầu hoạt động mới.", "Kết quả có thể khác tùy từng trường hợp."]),
    },
    "unpaid-wages": {
        "en": ("Gather evidence and seek help for wages that were not paid.", ["List the unpaid period and amount.", "Keep records of requests made to your employer.", "If unresolved, file a complaint with the labor office."], ["Employment contract", "Payslips", "Attendance records", "Bank statements", "Messages"], ["Keep the original evidence safe.", "Call 1345 if you also need visa or work-status advice."]),
        "vi": ("Thu thập bằng chứng và yêu cầu hỗ trợ khi chưa được trả lương.", ["Ghi lại thời gian và số tiền chưa trả.", "Lưu bằng chứng đã yêu cầu chủ sử dụng trả lương.", "Nếu chưa giải quyết, nộp đơn tại cơ quan lao động."], ["Hợp đồng lao động", "Phiếu lương", "Lịch sử chấm công", "Sao kê ngân hàng", "Tin nhắn"], ["Giữ an toàn bằng chứng gốc.", "Gọi 1345 nếu cần tư vấn thêm về cư trú hoặc việc làm."]),
    },
    "missing-contract": {
        "en": ("What to do if you did not receive a written employment contract.", ["Write down the agreed wage, hours, and start date.", "Ask your employer for a written contract.", "Get labor advice if they refuse or the terms differ."], ["Recruitment messages", "Work schedules", "Payment records", "Work instructions"], ["Check wages and hours before signing.", "Do not immediately sign a contract you do not understand."]),
        "vi": ("Cách xử lý khi chưa nhận được hợp đồng lao động bằng văn bản.", ["Ghi lại mức lương, giờ làm và ngày bắt đầu đã thỏa thuận.", "Yêu cầu chủ sử dụng giao hợp đồng bằng văn bản.", "Tư vấn lao động nếu bị từ chối hoặc nội dung khác thỏa thuận."], ["Tin nhắn tuyển dụng", "Lịch làm việc", "Lịch sử trả lương", "Chỉ thị công việc"], ["Kiểm tra lương và giờ làm trước khi ký.", "Không ký ngay hợp đồng mà bạn không hiểu."]),
    },
    "minimum-wage": {
        "en": ("Check whether your hourly pay meets the legal minimum wage.", ["Check the official minimum wage for the relevant year.", "Review your base pay and working hours on your payslip.", "Ask for advice if included wage items are unclear."], ["Employment contract", "Payslips", "Attendance records"], ["The minimum wage changes each year.", "Monthly pay must be compared using contractual working hours."]),
        "vi": ("Kiểm tra mức lương theo giờ có đạt mức tối thiểu theo luật hay không.", ["Kiểm tra mức lương tối thiểu chính thức của năm đó.", "Xem lương cơ bản và giờ làm trên phiếu lương.", "Tư vấn nếu các khoản lương không rõ ràng."], ["Hợp đồng lao động", "Phiếu lương", "Lịch sử chấm công"], ["Lương tối thiểu thay đổi mỗi năm.", "Lương tháng phải được so sánh theo giờ làm quy định."]),
    },
    "sudden-dismissal": {
        "en": ("Steps to take when you are dismissed without warning.", ["Request the reason and dismissal date in writing.", "Keep your contract and notification records.", "Contact the labor office or Labor Relations Commission."], ["Employment contract", "Dismissal notice", "Payslips", "Text or messenger records"], ["Do not write a resignation letter under pressure.", "There may be a deadline for filing a remedy request."]),
        "vi": ("Các bước xử lý khi bị sa thải đột ngột.", ["Yêu cầu lý do và ngày sa thải bằng văn bản.", "Giữ hợp đồng và bằng chứng thông báo.", "Liên hệ cơ quan lao động hoặc Ủy ban Quan hệ Lao động."], ["Hợp đồng lao động", "Thông báo sa thải", "Phiếu lương", "Tin nhắn"], ["Không viết đơn xin nghỉ việc do bị gây áp lực.", "Yêu cầu cứu xét có thể có thời hạn nộp."]),
    },
    "industrial-accident": {
        "en": ("Get treatment and claim workers' compensation for a work injury or illness.", ["For an emergency, call 119 or seek medical care immediately.", "Record when, where, and how it happened and any witnesses.", "Ask the compensation service about filing a claim."], ["Diagnosis and medical records", "Evidence from the accident scene", "Proof of employment", "Witness information"], ["You can seek help without your employer's approval.", "In an emergency, treatment comes before paperwork."]),
        "vi": ("Điều trị và yêu cầu bảo hiểm tai nạn khi bị thương hoặc bệnh do công việc.", ["Trong trường hợp khẩn cấp, gọi 119 hoặc đến cơ sở y tế ngay.", "Ghi thời gian, địa điểm, diễn biến và người chứng kiến.", "Tư vấn cơ quan bồi thường về việc nộp đơn."], ["Chẩn đoán và hồ sơ y tế", "Bằng chứng tại hiện trường", "Giấy tờ chứng minh quan hệ lao động", "Thông tin người chứng kiến"], ["Có thể yêu cầu hỗ trợ mà không cần chủ sử dụng đồng ý.", "Trong trường hợp khẩn cấp, điều trị là ưu tiên."]),
    },
    "working-hours-overtime": {
        "en": ("Check statutory working hours and overtime pay.", ["Check the agreed working hours in your contract.", "Track your actual hours with attendance records.", "Check your payslip for overtime, night, and holiday premiums.", "If something looks wrong, contact 1350 or the labor office."], ["Employment contract", "Attendance records", "Payslips"], ["Overtime has legal limits and premium-pay rules.", "Whether a violation occurred must be confirmed by the authorities."]),
        "vi": ("Kiểm tra giờ làm việc theo luật và phụ cấp tăng ca.", ["Kiểm tra giờ làm việc thỏa thuận trong hợp đồng.", "Ghi lại giờ làm thực tế bằng lịch chấm công.", "Kiểm tra phiếu lương về phụ cấp tăng ca, làm đêm, ngày nghỉ.", "Nếu có vấn đề, liên hệ 1350 hoặc cơ quan lao động."], ["Hợp đồng lao động", "Lịch sử chấm công", "Phiếu lương"], ["Tăng ca có giới hạn pháp lý và quy định phụ cấp.", "Việc vi phạm hay không cần cơ quan chức năng xác nhận."]),
    },
    "holiday-work": {
        "en": ("Understand paid holidays and holiday-work premiums.", ["Check the holiday terms in your contract.", "Record the dates and hours you worked on holidays.", "Check your payslip for holiday-work premiums.", "Contact 1350 if pay looks incorrect."], ["Employment contract", "Work schedule records", "Payslips"], ["Premiums may apply to holiday work.", "Standards vary by workplace and contract, so confirm officially."]),
        "vi": ("Tìm hiểu ngày nghỉ có lương và phụ cấp làm việc ngày nghỉ.", ["Kiểm tra điều khoản ngày nghỉ trong hợp đồng.", "Ghi lại ngày và giờ đã làm việc vào ngày nghỉ.", "Kiểm tra phiếu lương về phụ cấp ngày nghỉ.", "Liên hệ 1350 nếu tiền lương có vấn đề."], ["Hợp đồng lao động", "Lịch làm việc", "Phiếu lương"], ["Làm việc ngày nghỉ có thể được phụ cấp thêm.", "Tiêu chuẩn khác nhau theo nơi làm việc, cần xác nhận chính thức."]),
    },
    "annual-leave": {
        "en": ("Check your paid annual leave entitlement and how to use it.", ["Check your tenure and attendance rate.", "Ask how to request leave at your workplace.", "Keep records of leave requests and approvals.", "Contact 1350 if leave is refused without reason."], ["Employment contract", "Attendance records", "Leave request records"], ["Annual leave days depend on tenure and attendance.", "Unused-leave rules follow the law and your contract."]),
        "vi": ("Kiểm tra quyền nghỉ phép năm có lương và cách sử dụng.", ["Kiểm tra thời gian làm việc và tỷ lệ đi làm.", "Hỏi cách đăng ký nghỉ phép tại nơi làm việc.", "Giữ hồ sơ đăng ký và phê duyệt nghỉ phép.", "Liên hệ 1350 nếu bị từ chối không lý do."], ["Hợp đồng lao động", "Lịch sử chấm công", "Hồ sơ xin nghỉ phép"], ["Số ngày nghỉ phép phụ thuộc thời gian làm việc.", "Quy định phép chưa dùng theo luật và hợp đồng."]),
    },
}


def make_guide(id: str, category: str, titles: tuple[str, str, str], summary: str, steps: list[str], documents: list[str], cautions: list[str], agencies: list[str], source: tuple[str, str]) -> Guide:
    ko, en, vi = titles
    en_content = TRANSLATIONS[id]["en"]
    vi_content = TRANSLATIONS[id]["vi"]
    source_names = {"하이코리아": ("Hi Korea", "Hi Korea"), "출입국·외국인정책본부": ("Korea Immigration Service", "Cục Quản lý Xuất nhập cảnh Hàn Quốc"), "고용노동부": ("Ministry of Employment and Labor", "Bộ Việc làm và Lao động"), "최저임금위원회": ("Minimum Wage Commission", "Ủy ban Lương tối thiểu"), "근로복지공단": ("Workers' Compensation Service", "Cơ quan Bồi thường Lao động")}
    source_en, source_vi = source_names[source[0]]
    return Guide(id=id, category=category, title={"ko": ko, "en": en, "vi": vi}, summary={"ko": summary, "en": en_content[0], "vi": vi_content[0]}, steps={"ko": steps, "en": en_content[1], "vi": vi_content[1]}, required_documents={"ko": documents, "en": en_content[2], "vi": vi_content[2]}, cautions={"ko": cautions, "en": en_content[3], "vi": vi_content[3]}, agency_ids=agencies, source_name={"ko": source[0], "en": source_en, "vi": source_vi}, source_url=source[1], verified_at="2026-09-12")


HIKOREA = ("하이코리아", "https://www.hikorea.go.kr/")
MOEL = ("고용노동부", "https://www.moel.go.kr/")

GUIDES = [
    make_guide("alien-registration", "residency", ("외국인등록", "Alien registration", "Đăng ký người nước ngoài"), "한국에서 장기간 체류할 때 필요한 외국인등록 절차입니다.", ["등록 기한과 관할 출입국기관을 확인합니다.", "방문예약 후 준비서류를 가지고 신청합니다.", "심사 후 외국인등록증을 수령합니다."], ["여권", "통합신청서", "체류지 입증서류", "체류자격별 추가서류", "수수료"], ["체류자격마다 추가서류가 다릅니다.", "법정 신고기한을 넘기지 마세요."], ["immigration", "hikorea"], HIKOREA),
    make_guide("stay-extension", "residency", ("체류기간 연장", "Extension of stay", "Gia hạn thời gian cư trú"), "체류기간 만료 전에 연장 신청하는 방법입니다.", ["등록증의 체류 만료일을 확인합니다.", "온라인 또는 방문 신청 가능 여부를 확인합니다.", "기한 전에 서류와 수수료를 제출합니다."], ["여권", "외국인등록증", "통합신청서", "체류자격별 소명서류"], ["만료일이 지나면 불이익이 생길 수 있습니다.", "온라인 신청 대상이 아닌 경우도 있습니다."], ["immigration", "hikorea"], HIKOREA),
    make_guide("change-of-address", "residency", ("체류지 변경", "Change of address", "Thay đổi địa chỉ cư trú"), "이사 후 새 체류지를 신고하는 절차입니다.", ["새 주소의 증빙을 준비합니다.", "행정복지센터·출입국기관 또는 온라인 신고 가능 여부를 확인합니다.", "신고 완료 여부를 확인합니다."], ["여권", "외국인등록증", "체류지 입증서류", "통합신청서"], ["이사한 날부터 신고기한을 계산합니다.", "실제 거주지를 입증할 수 있어야 합니다."], ["immigration", "hikorea"], HIKOREA),
    make_guide("registration-card-reissue", "residency", ("외국인등록증 재발급", "Residence card reissue", "Cấp lại thẻ cư trú"), "등록증을 잃어버리거나 훼손했을 때 재발급받는 절차입니다.", ["재발급 사유를 확인합니다.", "방문예약 후 관할 출입국기관에 신청합니다.", "접수증을 보관하고 새 등록증을 수령합니다."], ["여권", "통합신청서", "사진", "재발급 사유 자료", "수수료"], ["분실한 경우 정해진 기간 안에 신청하세요.", "사진 규격을 미리 확인하세요."], ["immigration"], ("출입국·외국인정책본부", "https://www.immigration.go.kr/")),
    make_guide("status-change", "residency", ("체류자격 변경", "Change of status", "Thay đổi tư cách lưu trú"), "유학·취업 등 활동 목적이 바뀔 때 체류자격을 변경하는 절차입니다.", ["희망 체류자격의 요건을 확인합니다.", "자격별 필수서류를 준비해 신청합니다.", "허가 전까지 현재 자격의 활동 범위를 지킵니다."], ["여권", "외국인등록증", "통합신청서", "자격변경 입증서류", "수수료"], ["새 활동을 시작하기 전 허가 필요 여부를 확인하세요.", "개별 상황에 따라 심사 결과가 달라질 수 있습니다."], ["immigration", "hikorea"], HIKOREA),
    make_guide("unpaid-wages", "labor", ("임금체불", "Unpaid wages", "Nợ lương"), "받지 못한 임금의 증거를 모으고 상담·신고하는 방법입니다.", ["미지급 기간과 금액을 정리합니다.", "사업주에게 지급을 요청한 기록을 남깁니다.", "해결되지 않으면 노동관서에 진정합니다."], ["근로계약서", "급여명세서", "출퇴근 기록", "통장내역", "메시지"], ["증거 원본을 안전하게 보관하세요.", "체류·취업 상담은 1345에 문의할 수 있습니다."], ["labor-office", "danuri"], MOEL),
    make_guide("missing-contract", "labor", ("근로계약서 미작성", "Missing written contract", "Không có hợp đồng lao động"), "서면 근로계약서를 받지 못했을 때 확인할 사항입니다.", ["임금과 근무시간 등 합의 내용을 정리합니다.", "사업주에게 서면 계약서 교부를 요청합니다.", "거부하거나 내용이 다르면 상담을 받습니다."], ["채용 메시지", "근무 일정", "급여 입금내역", "업무 지시 기록"], ["서명 전 임금과 근로시간을 확인하세요.", "이해하기 어려운 계약에는 바로 서명하지 마세요."], ["labor-office", "danuri"], MOEL),
    make_guide("minimum-wage", "labor", ("최저임금 확인", "Check minimum wage", "Kiểm tra lương tối thiểu"), "내 시급이 법정 최저임금 이상인지 확인하는 방법입니다.", ["해당 연도의 공식 최저임금을 확인합니다.", "급여명세서에서 기본급과 근로시간을 확인합니다.", "임금 항목이 불분명하면 상담합니다."], ["근로계약서", "급여명세서", "출퇴근 기록"], ["최저임금은 매년 달라집니다.", "월급은 소정근로시간 등을 반영해 비교해야 합니다."], ["labor-office"], ("최저임금위원회", "https://www.minimumwage.go.kr/")),
    make_guide("sudden-dismissal", "labor", ("갑작스러운 해고", "Sudden dismissal", "Bị sa thải đột ngột"), "예고 없이 해고 통보를 받았을 때 대응 순서입니다.", ["해고 사유와 날짜를 서면으로 요청합니다.", "계약서와 통보 기록을 보관합니다.", "노동관서 또는 노동위원회 상담을 받습니다."], ["근로계약서", "해고 통지", "급여명세서", "문자·메신저 기록"], ["감정적으로 사직서를 작성하지 마세요.", "구제신청에는 기간 제한이 있을 수 있습니다."], ["labor-office", "danuri"], MOEL),
    make_guide("industrial-accident", "labor", ("산업재해", "Industrial accident", "Tai nạn lao động"), "일하다 다치거나 질병이 생겼을 때 치료와 산재 신청을 안내합니다.", ["위급하면 즉시 119 또는 의료기관의 도움을 받습니다.", "사고 경위와 목격자를 기록합니다.", "근로복지공단에 산재 신청을 상담합니다."], ["진단서·의무기록", "사고 현장 자료", "근로관계 입증자료", "목격자 정보"], ["사업주 동의 없이도 산재 신청 상담이 가능합니다.", "응급 상황에서는 치료가 먼저입니다."], ["workers-comp", "labor-office"], ("근로복지공단", "https://www.comwel.or.kr/")),
    make_guide("working-hours-overtime", "labor", ("근로시간과 연장근로", "Working hours & overtime", "Giờ làm việc & tăng ca"), "법정 근로시간과 연장근로 수당을 확인하는 방법입니다.", ["근로계약서의 소정근로시간을 확인합니다.", "출퇴근 기록으로 실제 근로시간을 정리합니다.", "연장·야간·휴일근로 수당 지급 여부를 급여명세서에서 확인합니다.", "문제가 있으면 1350 또는 관할 노동관서에 상담합니다."], ["근로계약서", "출퇴근 기록", "급여명세서"], ["연장근로에는 법령상 한도와 가산수당 기준이 있습니다.", "구체적인 위반 여부는 기관 확인이 필요합니다."], ["labor-office", "danuri"], MOEL),
    make_guide("holiday-work", "labor", ("휴일과 휴일근무", "Holidays & holiday work", "Ngày nghỉ & làm việc ngày nghỉ"), "휴일 보장과 휴일근무 수당을 확인하는 방법입니다.", ["근로계약서의 휴일 조항을 확인합니다.", "휴일에 일한 날짜와 시간을 기록합니다.", "급여명세서에서 휴일근무 수당 지급 여부를 확인합니다.", "지급에 문제가 있으면 1350에 상담합니다."], ["근로계약서", "근무 일정 기록", "급여명세서"], ["휴일 근무에는 가산수당이 적용될 수 있습니다.", "기준은 사업장과 계약에 따라 다르므로 공식 확인이 필요합니다."], ["labor-office", "danuri"], MOEL),
    make_guide("annual-leave", "labor", ("연차휴가 사용", "Annual leave", "Nghỉ phép năm"), "연차 유급휴가 발생 요건과 사용 방법을 확인합니다.", ["근무 기간과 출근율을 확인합니다.", "사업장의 연차 신청 방법을 확인합니다.", "연차 신청과 승인 기록을 남깁니다.", "이유 없이 거부되면 1350에 상담합니다."], ["근로계약서", "출근 기록", "연차 신청 기록"], ["연차 일수는 근무 기간과 출근율에 따라 달라집니다.", "미사용 연차 처리는 법령과 계약 기준을 따릅니다."], ["labor-office", "danuri"], MOEL),
]

# ---- Guide detail enrichment: target audience, common mistakes, official references ----

GUIDE_TARGETS = {
    "alien-registration": {"ko": "한국에 장기 체류를 시작하는 외국인", "en": "Foreign nationals starting a long-term stay in Korea", "vi": "Người nước ngoài bắt đầu cư trú dài hạn tại Hàn Quốc"},
    "stay-extension": {"ko": "체류 만료일이 다가오는 등록 외국인", "en": "Registered residents whose stay is about to expire", "vi": "Người đã đăng ký sắp hết hạn cư trú"},
    "change-of-address": {"ko": "이사한 등록 외국인", "en": "Registered residents who have moved", "vi": "Người đã đăng ký vừa chuyển nhà"},
    "registration-card-reissue": {"ko": "등록증을 잃어버렸거나 훼손한 외국인", "en": "Residents with a lost or damaged card", "vi": "Người bị mất hoặc hỏng thẻ cư trú"},
    "status-change": {"ko": "활동 목적이 바뀌는 외국인(유학→취업 등)", "en": "Residents whose purpose of stay is changing", "vi": "Người thay đổi mục đích lưu trú"},
    "unpaid-wages": {"ko": "임금을 받지 못한 근로자", "en": "Workers with unpaid wages", "vi": "Người lao động chưa được trả lương"},
    "missing-contract": {"ko": "서면 계약서를 받지 못한 근로자", "en": "Workers without a written contract", "vi": "Người lao động không có hợp đồng bằng văn bản"},
    "minimum-wage": {"ko": "시급·월급이 적정한지 확인하려는 근로자", "en": "Workers checking their pay level", "vi": "Người lao động muốn kiểm tra mức lương"},
    "sudden-dismissal": {"ko": "갑작스럽게 해고 통보를 받은 근로자", "en": "Workers dismissed without notice", "vi": "Người lao động bị sa thải đột ngột"},
    "industrial-accident": {"ko": "일하다 다치거나 질병이 생긴 근로자", "en": "Workers injured or ill from work", "vi": "Người lao động bị thương hoặc bệnh do công việc"},
    "working-hours-overtime": {"ko": "장시간 근무나 수당 문제가 걱정되는 근로자", "en": "Workers concerned about hours or overtime pay", "vi": "Người lao động lo về giờ làm và phụ cấp"},
    "holiday-work": {"ko": "휴일에도 일하는 근로자", "en": "Workers who work on holidays", "vi": "Người lao động làm việc vào ngày nghỉ"},
    "annual-leave": {"ko": "연차 사용이 어려운 근로자", "en": "Workers who cannot use annual leave", "vi": "Người lao động khó sử dụng nghỉ phép"},
}

GUIDE_MISTAKES = {
    "alien-registration": {"ko": ["신고 기한을 지나서 신청하는 경우", "체류자격별 추가서류를 준비하지 않는 경우"], "en": ["Applying after the deadline", "Missing status-specific documents"], "vi": ["Nộp sau thời hạn", "Thiếu giấy tờ theo tư cách lưu trú"]},
    "stay-extension": {"ko": ["만료일이 지난 뒤에 신청하는 경우", "온라인 신청 대상 여부를 확인하지 않는 경우"], "en": ["Applying after expiry", "Not checking online eligibility"], "vi": ["Nộp sau khi hết hạn", "Không kiểm tra điều kiện nộp trực tuyến"]},
    "change-of-address": {"ko": ["이사 후 신고를 미루는 경우", "실제 거주를 증명할 서류를 준비하지 않는 경우"], "en": ["Delaying the report after moving", "No proof of actual residence"], "vi": ["Trì hoãn khai báo sau khi chuyển nhà", "Không có giấy tờ chứng minh nơi ở"]},
    "registration-card-reissue": {"ko": ["분실 후 재발급 신청을 미루는 경우", "사진 규격을 확인하지 않는 경우"], "en": ["Delaying reissue after loss", "Wrong photo specifications"], "vi": ["Trì hoãn xin cấp lại sau khi mất", "Sai quy cách ảnh"]},
    "status-change": {"ko": ["허가 전에 새 활동을 시작하는 경우", "요건을 확인하지 않고 신청하는 경우"], "en": ["Starting the new activity before approval", "Applying without checking requirements"], "vi": ["Bắt đầu hoạt động mới trước khi được phép", "Nộp mà không kiểm tra điều kiện"]},
    "unpaid-wages": {"ko": ["증거 없이 구두로만 항의하는 경우", "원본 자료를 사업주에게 넘겨주는 경우"], "en": ["Complaining verbally without evidence", "Handing original evidence to the employer"], "vi": ["Chỉ phản đối bằng lời, không có bằng chứng", "Đưa bản gốc bằng chứng cho chủ"]},
    "missing-contract": {"ko": ["이해하지 못한 계약서에 서명하는 경우", "합의 내용을 기록으로 남기지 않는 경우"], "en": ["Signing a contract you do not understand", "Not recording the agreed terms"], "vi": ["Ký hợp đồng không hiểu rõ", "Không ghi lại nội dung thỏa thuận"]},
    "minimum-wage": {"ko": ["수당을 포함해 시급을 계산하는 경우", "해당 연도 기준을 확인하지 않는 경우"], "en": ["Including allowances in the hourly rate", "Not checking the current-year rate"], "vi": ["Tính phụ cấp vào lương giờ", "Không kiểm tra mức của năm hiện tại"]},
    "sudden-dismissal": {"ko": ["압박 속에 사직서를 쓰는 경우", "해고 통보 기록을 남기지 않는 경우"], "en": ["Writing a resignation letter under pressure", "Not keeping dismissal records"], "vi": ["Viết đơn xin nghỉ do bị ép", "Không giữ bằng chứng sa thải"]},
    "industrial-accident": {"ko": ["치료보다 서류를 먼저 챙기는 경우", "사업주 동의가 필요하다고 오해하는 경우"], "en": ["Prioritizing paperwork over treatment", "Assuming employer approval is required"], "vi": ["Ưu tiên giấy tờ hơn điều trị", "Tưởng cần chủ đồng ý mới được nộp"]},
    "working-hours-overtime": {"ko": ["출퇴근 기록을 남기지 않는 경우", "수당 없이 연장근로를 계속하는 경우"], "en": ["Not keeping attendance records", "Continuing unpaid overtime"], "vi": ["Không ghi lại giờ làm", "Tiếp tục tăng ca không phụ cấp"]},
    "holiday-work": {"ko": ["휴일 근무 기록을 남기지 않는 경우", "수당 미지급을 그냥 넘어가는 경우"], "en": ["Not recording holiday work", "Ignoring missing premiums"], "vi": ["Không ghi lại làm việc ngày nghỉ", "Bỏ qua phụ cấp bị thiếu"]},
    "annual-leave": {"ko": ["연차 신청 기록을 남기지 않는 경우", "미사용 연차 처리를 확인하지 않는 경우"], "en": ["Not recording leave requests", "Not checking unused-leave rules"], "vi": ["Không lưu hồ sơ xin nghỉ", "Không kiểm tra quy định phép chưa dùng"]},
}

GUIDE_RELATED_DOCS = {
    "alien-registration": ["hikorea-alien-registration"],
    "stay-extension": ["hikorea-stay-extension-application", "hikorea-stay-extension-status"],
    "change-of-address": ["gov24-address-change-report"],
    "registration-card-reissue": ["immigration-residence-card-loss-reissue"],
    "status-change": ["hikorea-status-change-permission"],
    "unpaid-wages": ["moel-unpaid-wage-claim", "moel-unpaid-dismissal-together"],
    "missing-contract": ["moel-written-employment-contract"],
    "minimum-wage": ["minimumwage-check-guide"],
    "sudden-dismissal": ["moel-unpaid-dismissal-together"],
    "working-hours-overtime": ["moel-overtime-limit", "moel-employment-contract-working-hours"],
    "holiday-work": ["moel-holiday-work"],
    "annual-leave": ["moel-annual-leave"],
}


def _enrich_guides() -> None:
    from ..retrieval.rag import SAMPLE_DOCUMENTS
    from ..core.schemas import GuideReference
    documents = {document.document_id: document for document, _ in SAMPLE_DOCUMENTS}
    for index, guide in enumerate(GUIDES):
        references = [GuideReference(title=documents[doc_id].title, url=documents[doc_id].source_url, publisher=documents[doc_id].publisher) for doc_id in GUIDE_RELATED_DOCS.get(guide.id, []) if doc_id in documents]
        GUIDES[index] = guide.model_copy(update={"target": GUIDE_TARGETS.get(guide.id, {}), "common_mistakes": GUIDE_MISTAKES.get(guide.id, {}), "related_documents": references})


_enrich_guides()
