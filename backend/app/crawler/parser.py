# 상세 페이지 파싱(제목·본문 추출, 메뉴/푸터 제거, 게시일·언어 감지, 링크 수집, PDF 텍스트)을 담당하는 파일
"""HTML/PDF extraction for crawled official pages. Standard library only.

Government sites bury a small article inside a large menu shell, so text is
collected in two passes: segments under a content-ish container (id/class hints
like "content", "board", "view") win; if no such container exists we fall back
to whole-page text excluding anchor text (menus are almost entirely links)."""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

# NOTE: "form" must NOT be skipped — Korean government boards wrap the whole
# list/detail markup in <form name="listForm">; individual controls are skipped.
SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "noscript", "select", "button", "iframe", "title", "option", "label", "input", "textarea"}
SKIP_HINTS = ("gnb", "lnb", "snb", "footer", "header", "breadcrumb", "banner", "copyright", "sitemap", "menu", "paging", "pagination", "quick", "sns", "share", "skip", "util", "allmenu", "popup", "location", "login")
CONTENT_HINTS = ("content", "conts", "board", "view", "article", "faq", "bbs", "txt", "detail", "guide", "sub_")
TITLE_HINTS = ("tit", "subject", "question", "sbj")


@dataclass
class ParsedPage:
    title: str = ""
    body: str = ""
    published_at: str | None = None
    links: list[tuple[str, str]] = field(default_factory=list)


VOID_TAGS = {"br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr", "param"}


class _Frame:
    __slots__ = ("tag", "skip", "content", "anchor_href", "anchor_text", "capture", "capture_kind")

    def __init__(self, tag: str):
        self.tag = tag
        self.skip = False
        self.content = False
        self.anchor_href: str | None = None
        self.anchor_text: list[str] | None = None
        self.capture: list[str] | None = None
        self.capture_kind = ""


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[tuple[str, bool, bool]] = []  # (text, in_content, in_anchor)
        self.links: list[tuple[str, str]] = []
        self.title_tag = ""
        self.og_title = ""
        self.headings: list[str] = []
        self.title_hint_texts: list[str] = []
        self._stack: list[_Frame] = []
        self._skip_depth = 0
        self._content_depth = 0
        self._anchor_depth = 0
        self._in_title_tag = False

    @staticmethod
    def _attr_blob(attrs) -> str:
        return " ".join(str(value) for key, value in attrs if key in ("id", "class") and value).lower()

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "meta":
            attr_map = dict(attrs)
            if (attr_map.get("property") or attr_map.get("name")) == "og:title" and attr_map.get("content"):
                self.og_title = unescape(attr_map["content"]).strip()
            return
        if tag in VOID_TAGS:
            return
        if tag == "title":
            self._in_title_tag = True
            return
        frame = _Frame(tag)
        blob = self._attr_blob(attrs)
        frame.skip = tag in SKIP_TAGS or any(hint in blob for hint in SKIP_HINTS)
        if frame.skip or self._skip_depth:
            # Menu/nav containers are excluded from BODY text, but their links are
            # still list->detail navigation (many sites keep content links in menus).
            if tag == "a":
                href = (dict(attrs).get("href") or "").strip()
                if href:
                    self.links.append((href, ""))
        if frame.skip:
            self._skip_depth += 1
        elif not self._skip_depth:
            if any(hint in blob for hint in CONTENT_HINTS):
                frame.content = True
                self._content_depth += 1
            if tag == "a":
                frame.anchor_href = (dict(attrs).get("href") or "").strip()
                frame.anchor_text = []
                self._anchor_depth += 1
            if tag in ("h1", "h2", "h3", "h4"):
                frame.capture = []
                frame.capture_kind = "heading"
            elif any(hint in blob for hint in TITLE_HINTS):
                frame.capture = []
                frame.capture_kind = "title_hint"
        self._stack.append(frame)

    def _pop_frame(self, frame: _Frame) -> None:
        if frame.skip:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if frame.content:
            self._content_depth = max(0, self._content_depth - 1)
        if frame.anchor_text is not None:
            self._anchor_depth = max(0, self._anchor_depth - 1)
            if frame.anchor_href:
                self.links.append((frame.anchor_href, " ".join(frame.anchor_text).strip()))
        if frame.capture is not None:
            text = re.sub(r"\s+", " ", " ".join(frame.capture)).strip()
            if text:
                (self.headings if frame.capture_kind == "heading" else self.title_hint_texts).append(text)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title_tag = False
            return
        if tag in VOID_TAGS:
            return
        if not any(frame.tag == tag for frame in self._stack):
            return  # stray close tag: ignore instead of unwinding unrelated frames
        while self._stack:
            frame = self._stack.pop()
            self._pop_frame(frame)
            if frame.tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if self._in_title_tag:
            self.title_tag += data
            return
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        for frame in self._stack:
            if frame.anchor_text is not None:
                frame.anchor_text.append(text)
            if frame.capture is not None:
                frame.capture.append(text)
        self.segments.append((text, self._content_depth > 0, self._anchor_depth > 0))


def decode_body(body: bytes) -> str:
    """Decode with the page's declared charset; Korean gov sites still ship EUC-KR."""
    head = body[:4096].decode("ascii", errors="ignore")
    match = re.search(r'charset=["\']?\s*([\w-]+)', head, re.IGNORECASE)
    candidates = ([match.group(1)] if match else []) + ["utf-8", "cp949"]
    for encoding in candidates:
        try:
            return body.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")


GENERIC_TITLES = {"고용노동부", "정부24", "하이코리아", "최저임금위원회", "다누리", "메인", "홈", "faq",
                  "자주 묻는 질문", "자주하는 질문", "자주 하는 질문", "자주 하는 질문 상세", "질문과 답변", "상세보기", "상세 보기",
                  "서브 콘텐츠 시작", "본문 바로가기", "분야별 정보", "콘텐츠 시작", "인터넷상담", "빠른인터넷상담"}
DATE_LABEL_TITLE = re.compile(r"^(신청일|답변일|등록일|작성일|게시일|수정일|접수일|처리일|조회수?)\s*[:：]")


def _question_from_body(body: str) -> str:
    """FAQ boards label the actual question: 카테고리/질의/답변 — use the 질의 line as title."""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    for index, line in enumerate(lines[:12]):
        if line in ("질의", "질문", "질의내용", "Q", "문") and index + 1 < len(lines):
            question = lines[index + 1]
            if 6 <= len(question) <= 200:
                return question
    # Board-view layout: first line is the post title when a date-meta line follows it.
    if lines and 6 <= len(lines[0]) <= 200 and not DATE_LABEL_TITLE.match(lines[0]):
        if any(DATE_LABEL_TITLE.match(line) for line in lines[1:4]):
            return lines[0]
    return ""


def _pick_title(parser: _PageParser, body: str) -> str:
    question = _question_from_body(body)
    if question:
        return question
    candidates = [parser.og_title] + parser.headings + parser.title_hint_texts + [parser.title_tag.strip()]
    for candidate in candidates:
        cleaned = re.sub(r"\s+", " ", candidate or "").strip()
        if ">" in cleaned:  # breadcrumb: keep the deepest (most specific) segment
            cleaned = cleaned.split(">")[-1].strip()
        cleaned = re.split(r"\s*[|]\s*", cleaned)[0].strip()
        if 6 <= len(cleaned) <= 200 and cleaned.lower() not in GENERIC_TITLES and not DATE_LABEL_TITLE.match(cleaned):
            return cleaned
    first_line = next((line.strip() for line in body.splitlines() if len(line.strip()) >= 6 and not DATE_LABEL_TITLE.match(line.strip())), "")
    return first_line[:80]


DATE_LABELED = re.compile(r"(?:등록일|작성일|게시일|수정일|시행일|고시일)\s*[:.\s]*\s*(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})")
DATE_BARE = re.compile(r"\b(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})\b")


def extract_published_at(text: str) -> str | None:
    match = DATE_LABELED.search(text) or DATE_BARE.search(text)
    if not match:
        return None
    year, month, day = (int(group) for group in match.groups())
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def detect_language(text: str) -> str:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "ko"
    hangul = sum(1 for ch in letters if "가" <= ch <= "힣")
    if hangul / len(letters) >= 0.05:
        return "ko"
    vietnamese = set("ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệịỉĩọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ")
    if sum(1 for ch in text.lower() if ch in vietnamese) >= 3:
        return "vi"
    return "en"


def parse_page(html: str, base_url: str) -> ParsedPage:
    parser = _PageParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    # Anchor text is excluded even inside content containers: sidebar/topic menus
    # frequently live in the "contents" wrapper and would pollute the body with
    # hundreds of unrelated topic words (poisoning lexical AND vector search).
    content_segments = [text for text, in_content, in_anchor in parser.segments if in_content and not in_anchor]
    if len(" ".join(content_segments)) >= 120:
        body_parts = content_segments
    else:
        body_parts = [text for text, _, in_anchor in parser.segments if not in_anchor]
    body = "\n".join(body_parts)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n{2,}", "\n", body).strip()
    links = [(urljoin(base_url, href), text) for href, text in parser.links if href and not href.lower().startswith(("javascript:", "mailto:", "#", "tel:"))]
    return ParsedPage(title=_pick_title(parser, body), body=body, published_at=extract_published_at(html), links=links)


def extract_pdf_text(body: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(body))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
