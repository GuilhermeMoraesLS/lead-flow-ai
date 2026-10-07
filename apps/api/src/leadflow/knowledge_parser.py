"""Isolated text extraction for manager documents.

Runs as a child process (``python -I knowledge_parser.py <type>``) with the raw object on
stdin and JSON on stdout. An audit hook blocks sockets, processes and native loading before
any parser is imported; content is never executed and embedded links are never followed.
"""

import io
import json
import re
import sys
import zipfile
from typing import Any
from xml.etree import ElementTree

PARSER_VERSION = "sl11-v1"
MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 2_000_000
DOCX_MAX_ENTRIES = 1000
DOCX_MAX_UNCOMPRESSED = 50 * 1024 * 1024
DOCX_MAX_RATIO = 100
BLOCKED_EVENTS = ("socket.", "subprocess.", "os.system", "os.exec", "os.posix_spawn",
                  "os.spawn", "os.fork", "os.startfile", "ctypes.", "urllib.Request",
                  "webbrowser.")
PDF_ACTIVE = re.compile(rb"/(?:JavaScript|JS|Launch|EmbeddedFiles?|XFA|RichMedia|GoToE)"
                        rb"(?![A-Za-z0-9])")
PDF_ACTIONS = {"/JavaScript", "/Launch", "/GoToE", "/ImportData", "/RichMediaExecute"}
DOCX_EXTERNAL_ACTIVE = ("attachedTemplate", "oleObject", "frame", "subDocument")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class Rejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def install_guard() -> None:
    def hook(event: str, args: tuple[Any, ...]) -> None:
        if event.startswith(BLOCKED_EVENTS):
            raise RuntimeError("blocked by extraction sandbox: " + event)

    sys.addaudithook(hook)
    if sys.platform != "win32":  # Windows has no rlimits; the parent enforces a timeout.
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))


def sniff(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "docx"
    if b"\x00" in data:
        return "binary"
    return "text"


def extract(media_type: str, data: bytes) -> list[dict[str, Any]]:
    expected = {"pdf": "pdf", "docx": "docx", "txt": "text", "md": "text"}.get(media_type)
    if expected is None or sniff(data) != expected:
        raise Rejected("type_mismatch")
    if media_type == "pdf":
        sections = parse_pdf(data)
    elif media_type == "docx":
        sections = parse_docx(data)
    else:
        sections = parse_text(data, markdown=media_type == "md")
    sections = [s for s in sections if s["text"].strip()]
    if not sections:
        raise Rejected("no_text")
    if sum(len(s["text"]) for s in sections) > MAX_TEXT_CHARS:
        raise Rejected("text_too_large")
    return sections


def parse_text(data: bytes, markdown: bool) -> list[dict[str, Any]]:
    try:
        content = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Rejected("invalid_encoding") from None
    if not markdown:
        return [{"location": "", "text": content, "line": 1}]
    sections: list[dict[str, Any]] = []
    location, lines = "início", list[str]()
    for line in content.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if heading:
            sections.append({"location": location, "text": "\n".join(lines)})
            location, lines = "seção: " + heading.group(1)[:250], [heading.group(1)]
        else:
            lines.append(line)
    sections.append({"location": location, "text": "\n".join(lines)})
    return sections


def read_member(archive: zipfile.ZipFile, name: str, budget: list[int]) -> bytes:
    """Decompress with a hard cap; declared sizes in zip headers are not trusted."""
    output = bytearray()
    with archive.open(name) as member:
        while chunk := member.read(65536):
            output.extend(chunk)
            budget[0] -= len(chunk)
            if budget[0] < 0:
                raise Rejected("archive_limits")
    return bytes(output)


def parse_xml(data: bytes) -> ElementTree.Element:
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise Rejected("active_content")
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise Rejected("malformed") from None


def parse_docx(data: bytes) -> list[dict[str, Any]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise Rejected("malformed") from None
    infos = archive.infolist()
    names = {info.filename for info in infos}
    if "[Content_Types].xml" not in names or "word/document.xml" not in names:
        raise Rejected("type_mismatch")
    if len(infos) > DOCX_MAX_ENTRIES or sum(i.file_size for i in infos) > DOCX_MAX_UNCOMPRESSED:
        raise Rejected("archive_limits")
    for info in infos:
        name = info.filename.lower()
        if (name.endswith("vbaproject.bin") or name.startswith("word/activex/")
                or (name.startswith("word/embeddings/") and name.endswith(".bin"))):
            raise Rejected("active_content")
        if info.file_size > (1 << 20) and info.file_size > DOCX_MAX_RATIO * max(info.compress_size, 1):
            raise Rejected("archive_limits")
    budget = [DOCX_MAX_UNCOMPRESSED]
    if b"macroenabled" in read_member(archive, "[Content_Types].xml", budget).lower():
        raise Rejected("active_content")
    if "word/_rels/document.xml.rels" in names:
        rels = parse_xml(read_member(archive, "word/_rels/document.xml.rels", budget))
        for relation in rels.iter(RELS + "Relationship"):
            if (relation.get("TargetMode") == "External"
                    and relation.get("Type", "").endswith(DOCX_EXTERNAL_ACTIVE)):
                raise Rejected("active_content")
    document = parse_xml(read_member(archive, "word/document.xml", budget))
    sections: list[dict[str, Any]] = []
    location, paragraphs = "início", list[str]()
    for paragraph in document.iter(W + "p"):
        value = "".join(node.text or "" for node in paragraph.iter(W + "t")).strip()
        if not value:
            continue
        style = paragraph.find(f"{W}pPr/{W}pStyle")
        name = (style.get(W + "val") or "").lower() if style is not None else ""
        if name.startswith(("heading", "title", "titulo", "título")):
            sections.append({"location": location, "text": "\n".join(paragraphs)})
            location, paragraphs = "seção: " + value[:250], [value]
        else:
            paragraphs.append(value)
    sections.append({"location": location, "text": "\n".join(paragraphs)})
    return sections


def parse_pdf(data: bytes) -> list[dict[str, Any]]:
    if PDF_ACTIVE.search(data):
        raise Rejected("active_content")
    import pypdf  # Imported after the guard so no parser code runs unrestricted.

    try:
        reader = pypdf.PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise Rejected("encrypted")
        root: Any = reader.trailer["/Root"].get_object()
        names: Any = root.get("/Names")
        names = names.get_object() if names is not None else {}
        form: Any = root.get("/AcroForm")
        form = form.get_object() if form is not None else {}
        if ("/AA" in root or "/JavaScript" in names or "/EmbeddedFiles" in names
                or "/XFA" in form or action_is_active(root.get("/OpenAction"))):
            raise Rejected("active_content")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise Rejected("too_many_pages")
        sections = []
        for number, page in enumerate(reader.pages, start=1):
            if "/AA" in page:
                raise Rejected("active_content")
            for annotation in page.get("/Annots") or []:
                if action_is_active(annotation.get_object().get("/A")):
                    raise Rejected("active_content")
            sections.append({"location": f"página {number}", "text": page.extract_text() or ""})
        return sections
    except Rejected:
        raise
    except Exception:  # noqa: BLE001 - untrusted input must fail closed, never crash open
        raise Rejected("malformed") from None


def action_is_active(action: Any) -> bool:
    if action is None:
        return False
    action = action.get_object() if hasattr(action, "get_object") else action
    return isinstance(action, dict) and str(action.get("/S")) in PDF_ACTIONS


def main() -> None:
    install_guard()
    media_type = sys.argv[1] if len(sys.argv) > 1 else ""
    data = sys.stdin.buffer.read()
    try:
        result: dict[str, Any] = {"sections": extract(media_type, data),
                                  "parserVersion": PARSER_VERSION}
    except Rejected as rejected:
        result = {"error": rejected.code}
    except RecursionError, MemoryError:
        result = {"error": "archive_limits"}
    except RuntimeError as error:
        blocked = "extraction sandbox" in str(error)
        result = {"error": "active_content" if blocked else "malformed"}
    except Exception:  # noqa: BLE001 - any parser fault is reported as an unusable file
        result = {"error": "malformed"}
    sys.stdout.write(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
