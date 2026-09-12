# 출처 카드의 표시용 번역(영/베 제목·기관·요약) 사전을 담당하는 파일
"""Display-layer translations for source cards (en/vi).

The original title/publisher/source_url are NEVER replaced — these values are
an optional display layer so English/Vietnamese users can understand what each
official source is. Every summary is a faithful 1–2 sentence rendering of the
reviewed document text itself (no legal facts beyond the evidence). Curated as
a deterministic dictionary keyed by document_id: no LLM calls, works in every
fallback path, and stays in lockstep with the reviewed corpus.
"""

PUBLISHER_DISPLAY = {
    "고용노동부": {"en": "Ministry of Employment and Labor", "vi": "Bộ Việc làm và Lao động"},
    "최저임금위원회": {"en": "Minimum Wage Commission", "vi": "Hội đồng Tiền lương Tối thiểu"},
    "법무부 출입국·외국인정책본부": {"en": "Korea Immigration Service, Ministry of Justice", "vi": "Cục Xuất nhập cảnh, Bộ Tư pháp Hàn Quốc"},
    "하이코리아": {"en": "Hi Korea (immigration e-government portal)", "vi": "Hi Korea (cổng điện tử xuất nhập cảnh)"},
    "정부24": {"en": "Government24 (gov.kr)", "vi": "Government24 (gov.kr)"},
}

SOURCE_DISPLAY = {
    "hikorea-stay-extension-status": {
        "en": ("Checking a Stay-Extension Application on Hi Korea", "Explains how to check your stay expiry date and the progress and result of a stay-extension application through Hi Korea e-services, the competent immigration office, or the 1345 helpline."),
        "vi": ("Kiểm tra đơn gia hạn cư trú trên Hi Korea", "Giải thích cách kiểm tra ngày hết hạn cư trú và tiến độ, kết quả của đơn gia hạn qua dịch vụ điện tử Hi Korea, cơ quan xuất nhập cảnh phụ trách hoặc tổng đài 1345."),
    },
    "immigration-residence-card-correction": {
        "en": ("FAQ: Correcting Residence-Card Details", "Explains what to do when the name or personal details on your residence card differ from your passport: ask the competent immigration office whether correction is possible and what supporting documents are needed."),
        "vi": ("Hỏi đáp: Đính chính thông tin trên thẻ cư trú", "Giải thích cách xử lý khi tên hoặc thông tin cá nhân trên thẻ cư trú khác với hộ chiếu: hỏi cơ quan xuất nhập cảnh phụ trách về khả năng đính chính và giấy tờ chứng minh cần thiết."),
    },
    "hikorea-student-part-time-work": {
        "en": ("Part-Time Work Rules for International Students", "Explains that students must check permission requirements, allowed hours and workplaces, and required documents before starting part-time work; details vary by visa status, so confirm via 1345 or the immigration office."),
        "vi": ("Quy định làm thêm cho du học sinh", "Giải thích rằng du học sinh phải kiểm tra điều kiện cho phép, giờ và nơi làm việc, giấy tờ cần thiết trước khi làm thêm; chi tiết khác nhau theo tư cách lưu trú nên cần xác nhận qua 1345 hoặc cơ quan xuất nhập cảnh."),
    },
    "moel-employment-contract-working-hours": {
        "en": ("When Actual Working Hours Differ from the Contract", "Advises keeping attendance records, schedules, and payslips when actual hours differ from the contract, and consulting the 1350 helpline or the labor office if the issue is not resolved."),
        "vi": ("Khi giờ làm thực tế khác với hợp đồng", "Khuyên giữ lịch chấm công, lịch làm việc và phiếu lương khi giờ làm thực tế khác hợp đồng, và liên hệ tổng đài 1350 hoặc cơ quan lao động nếu vấn đề không được giải quyết."),
    },
    "moel-written-employment-contract": {
        "en": ("Written Statement and Delivery of Employment Terms", "States that key working conditions such as wages, working hours, and holidays must be put in writing and a copy given to the worker; keep evidence and consult 1350 if the written terms are missing or differ from reality."),
        "vi": ("Ghi rõ điều kiện lao động bằng văn bản và giao hợp đồng", "Nêu rằng các điều kiện chính như lương, giờ làm, ngày nghỉ phải được ghi bằng văn bản và giao một bản cho người lao động; giữ bằng chứng và hỏi 1350 nếu thiếu văn bản hoặc nội dung khác thực tế."),
    },
    "moel-wage-deduction-housing": {
        "en": ("Checking Housing-Cost Deductions from Wages", "Explains comparing the contract, payslips, consent documents, and actual payments when housing costs are deducted from wages; the legality of a deduction depends on the contract and the law, so consult 1350."),
        "vi": ("Kiểm tra khoản trừ tiền nhà từ lương", "Giải thích việc so sánh hợp đồng, phiếu lương, giấy đồng ý và số tiền thực nhận khi tiền nhà bị trừ vào lương; tính hợp pháp phụ thuộc hợp đồng và pháp luật nên hãy hỏi 1350."),
    },
    "moel-unpaid-dismissal-together": {
        "en": ("When Unpaid Wages and Dismissal Happen Together", "Advises keeping the contract, payslips, bank records, and dismissal notices together; wage issues go to the 1350 helpline and dismissal remedies to the Labor Relations Commission, each with its own requirements and deadlines."),
        "vi": ("Khi nợ lương và sa thải xảy ra cùng lúc", "Khuyên giữ hợp đồng, phiếu lương, sao kê và thông báo sa thải; vấn đề lương liên hệ 1350, cứu xét sa thải liên hệ Ủy ban Quan hệ Lao động, mỗi thủ tục có điều kiện và thời hạn riêng."),
    },
    "hikorea-alien-registration": {
        "en": ("Alien Registration Application Guide", "Explains that long-term residents must apply for alien registration at the competent immigration office within the required period, with documents and deadlines varying by visa status; confirm via 1345 or Hi Korea."),
        "vi": ("Hướng dẫn đăng ký người nước ngoài", "Giải thích rằng người cư trú dài hạn phải đăng ký người nước ngoài tại cơ quan xuất nhập cảnh trong thời hạn quy định; giấy tờ và thời hạn khác nhau theo tư cách lưu trú, xác nhận qua 1345 hoặc Hi Korea."),
    },
    "immigration-residence-card-loss-reissue": {
        "en": ("Lost Residence Card: Report and Reissue", "Explains applying for reissue at the competent immigration office within the required period after losing or damaging the card, preparing your passport, application form, photo, and fee."),
        "vi": ("Mất thẻ cư trú: khai báo và cấp lại", "Giải thích việc xin cấp lại tại cơ quan xuất nhập cảnh trong thời hạn quy định khi mất hoặc hỏng thẻ, chuẩn bị hộ chiếu, đơn, ảnh và lệ phí."),
    },
    "gov24-address-change-report": {
        "en": ("Reporting a Change of Residence", "Explains reporting your new address to the competent authority within the required period after moving, with your passport and residence card; online options can be checked on Government24 and Hi Korea."),
        "vi": ("Khai báo thay đổi nơi cư trú", "Giải thích việc khai báo địa chỉ mới với cơ quan phụ trách trong thời hạn quy định sau khi chuyển nhà, mang hộ chiếu và thẻ cư trú; có thể kiểm tra khai báo trực tuyến trên Government24 và Hi Korea."),
    },
    "hikorea-stay-extension-application": {
        "en": ("Applying for a Stay-Extension Permit", "Explains that a stay extension must be applied for before the expiry date, online or by reserved visit, with documents varying by visa status; eligibility can be confirmed via 1345."),
        "vi": ("Xin phép gia hạn thời gian cư trú", "Giải thích rằng phải nộp đơn gia hạn trước ngày hết hạn, trực tuyến hoặc đặt lịch đến trực tiếp; giấy tờ khác nhau theo tư cách lưu trú, có thể xác nhận điều kiện qua 1345."),
    },
    "hikorea-status-change-permission": {
        "en": ("Changing Your Status of Stay", "Explains that permission must be obtained before starting a new activity such as work or study, and that you must stay within your current status until the change is approved."),
        "vi": ("Thay đổi tư cách lưu trú", "Giải thích rằng phải được phép trước khi bắt đầu hoạt động mới như làm việc hoặc học tập, và phải tuân thủ tư cách hiện tại cho đến khi được chấp thuận."),
    },
    "minimumwage-check-guide": {
        "en": ("How to Check the Minimum Wage", "Explains checking your base pay and contractual hours on your contract and payslip and comparing your hourly pay with the officially announced minimum wage for the year; consult 1350 if wage items are unclear."),
        "vi": ("Cách kiểm tra lương tối thiểu", "Giải thích việc xem lương cơ bản và giờ làm quy định trên hợp đồng, phiếu lương rồi so sánh lương giờ với mức lương tối thiểu được công bố của năm; hỏi 1350 nếu các khoản chưa rõ."),
    },
    "moel-overtime-limit": {
        "en": ("Overtime and Working-Hour Limits", "States that overtime beyond statutory hours requires legal conditions including the parties' agreement and is subject to limits; keep attendance records and check payslips for overtime pay, consulting 1350 if needed."),
        "vi": ("Tăng ca và giới hạn giờ làm việc", "Nêu rằng làm thêm vượt giờ luật định cần đáp ứng điều kiện pháp lý gồm thỏa thuận của hai bên và có giới hạn; giữ lịch chấm công, kiểm tra phụ cấp trên phiếu lương và hỏi 1350 khi cần."),
    },
    "moel-holiday-work": {
        "en": ("Holiday Work and Holiday Pay", "States that holidays are guaranteed by law and contract and that premium pay may apply to holiday work; record the dates and hours worked and check your payslips, as standards vary by workplace."),
        "vi": ("Làm việc ngày nghỉ và phụ cấp ngày nghỉ", "Nêu rằng ngày nghỉ được bảo đảm theo luật và hợp đồng, làm việc ngày nghỉ có thể được phụ cấp; ghi lại ngày giờ đã làm và kiểm tra phiếu lương vì tiêu chuẩn khác nhau theo nơi làm việc."),
    },
    "moel-annual-leave": {
        "en": ("Using Paid Annual Leave", "Explains that workers meeting statutory conditions can use paid annual leave, with the number of days depending on tenure and attendance; rules for unused leave follow the law and the contract."),
        "vi": ("Sử dụng nghỉ phép năm có lương", "Giải thích rằng người lao động đủ điều kiện luật định được nghỉ phép năm có lương; số ngày phụ thuộc thời gian làm việc và chuyên cần, phép chưa dùng xử lý theo luật và hợp đồng."),
    },
    "moel-resignation-severance": {
        "en": ("Resignation Procedure and Severance Pay", "Advises checking the notice rules in your contract and workplace rules before resigning; workers with sufficient continuous service may be entitled to severance pay, and unpaid severance can be reported as wage arrears."),
        "vi": ("Thủ tục thôi việc và trợ cấp thôi việc", "Khuyên kiểm tra quy định thông báo trong hợp đồng và nội quy trước khi nghỉ; người làm đủ thời gian liên tục có thể được trợ cấp thôi việc, nếu không được trả có thể khiếu nại như nợ lương."),
    },
    "moel-unpaid-wage-claim": {
        "en": ("Filing a Wage-Arrears Complaint", "Explains organizing the unpaid period and amount, keeping the contract, payslips, attendance and bank records, and filing a complaint with the Ministry of Employment and Labor or the competent labor office; guidance is available via 1350."),
        "vi": ("Nộp đơn khiếu nại nợ lương", "Giải thích việc tổng hợp thời gian và số tiền chưa trả, giữ hợp đồng, phiếu lương, chấm công và sao kê, rồi nộp đơn khiếu nại tới Bộ Việc làm và Lao động hoặc cơ quan lao động; được hướng dẫn qua 1350."),
    },
    "minimumwage-2026-notice": {
        "en": ("2026 Minimum Wage Notice", "States that the official minimum wage for 2026 is KRW 10,320 per hour, applying to all workplaces regardless of business type; contract terms below this rate may be denied effect."),
        "vi": ("Thông báo lương tối thiểu năm 2026", "Nêu rằng lương tối thiểu chính thức năm 2026 là 10.320 won/giờ, áp dụng cho mọi nơi làm việc; phần hợp đồng thấp hơn mức này có thể không có hiệu lực."),
    },
    "moel-overtime-premium-standard": {
        "en": ("Premium-Pay Standards for Overtime, Night, and Holiday Work", "States that workplaces with five or more regular employees must pay at least a 50% premium for overtime, with premiums also applying to night work (10 p.m.–6 a.m.) and holiday work; workplaces with fewer than five employees are exempt."),
        "vi": ("Tiêu chuẩn phụ cấp tăng ca, làm đêm và ngày nghỉ", "Nêu rằng nơi làm việc từ 5 nhân viên trở lên phải trả phụ cấp ít nhất 50% cho tăng ca; làm đêm (22h–6h) và ngày nghỉ cũng có phụ cấp, nơi dưới 5 người không áp dụng."),
    },
    "moel-working-hours-standard": {
        "en": ("Statutory Working-Hour and Break Standards", "States the statutory limits of 8 hours per day and 40 per week excluding breaks, up to 12 weekly overtime hours by agreement, and required breaks of at least 30 minutes per 4 hours of work."),
        "vi": ("Tiêu chuẩn giờ làm việc và giờ nghỉ theo luật", "Nêu giới hạn luật định 8 giờ/ngày và 40 giờ/tuần không kể giờ nghỉ, được làm thêm tối đa 12 giờ/tuần khi có thỏa thuận, và phải cho nghỉ ít nhất 30 phút mỗi 4 giờ làm."),
    },
    "moel-weekly-holiday-standard": {
        "en": ("Paid Weekly Holiday Standard", "States that a worker who completes the scheduled workdays in a week is guaranteed at least one paid holiday per week on average; this does not apply to workers averaging under 15 scheduled hours per week."),
        "vi": ("Tiêu chuẩn ngày nghỉ tuần có lương", "Nêu rằng người làm đủ các ngày làm việc quy định trong tuần được bảo đảm trung bình ít nhất một ngày nghỉ có lương mỗi tuần; không áp dụng cho người làm dưới 15 giờ/tuần."),
    },
    "moel-annual-leave-standard": {
        "en": ("Annual Paid-Leave Accrual Standard", "States that a worker with one year of service and at least 80% attendance receives 15 days of paid leave, and a worker with under one year receives one day per full month of attendance; applies to workplaces with five or more employees."),
        "vi": ("Tiêu chuẩn phát sinh nghỉ phép năm có lương", "Nêu rằng người làm đủ một năm với chuyên cần từ 80% được 15 ngày phép có lương, người làm dưới một năm được một ngày cho mỗi tháng đi làm đầy đủ; áp dụng cho nơi làm việc từ 5 người trở lên."),
    },
    "moel-wage-cut-penalty-prohibition": {
        "en": ("Full Payment of Wages and Prohibition of Predetermined Penalties", "States that wages must be paid directly to the worker in full, subject only to exceptions provided by law or collective agreement, and that contracts predetermining penalties or damages for breach may not be concluded."),
        "vi": ("Thanh toán đầy đủ tiền lương và cấm thỏa thuận trước tiền phạt", "Nêu rằng lương phải được trả đủ trực tiếp cho người lao động trừ ngoại lệ theo luật hoặc thỏa ước tập thể, và không được ký hợp đồng định trước tiền phạt hoặc bồi thường khi vi phạm."),
    },
    "moel-internal-rules-limit": {
        "en": ("Workplace Rules and Their Limits under the Law", "States that workplace rules and internal regulations may not contradict the law or the applicable collective agreement, and that any part falling below mandatory legal standards may be denied effect."),
        "vi": ("Nội quy công ty và giới hạn theo pháp luật", "Nêu rằng nội quy và quy định nội bộ không được trái pháp luật hoặc thỏa ước tập thể áp dụng; phần thấp hơn tiêu chuẩn bắt buộc có thể không có hiệu lực."),
    },
}


def display_fields(document_id: str, publisher: str, language: str) -> tuple[str | None, str | None, str | None]:
    """(display_title, display_publisher, source_summary) for en/vi; None triple for ko/unknown."""
    if language not in ("en", "vi"):
        return None, None, None
    display_publisher = PUBLISHER_DISPLAY.get(publisher, {}).get(language)
    entry = SOURCE_DISPLAY.get(document_id, {}).get(language)
    if entry:
        return entry[0], display_publisher, entry[1]
    return None, display_publisher, None
