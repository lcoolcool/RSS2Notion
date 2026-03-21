"""
内容转换：HTML → Markdown 块，Markdown → Notion Blocks
"""

import json
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from mistletoe import Document
from mistletoe.ast_renderer import AstRenderer


# ─────────────────────────────────────────────
# HTML 拆分：文字段落 + 图片 交替输出
# ─────────────────────────────────────────────
def split_html_to_blocks(html: str) -> list[tuple]:
    """
    把 HTML 拆成交替的 ("text", markdown) 和 ("image", url) 块。
    核心思路：用 BeautifulSoup 遍历顶层节点，遇到 <img> 单独提出，
    其余节点转 Markdown。
    """
    soup = BeautifulSoup(html, "html.parser")
    result: list[tuple] = []
    pending_html = []

    def flush_pending():
        """把积累的 HTML 节点转成 Markdown 并加入结果"""
        if not pending_html:
            return
        combined = "".join(str(n) for n in pending_html)
        text = md(combined, heading_style="ATX",
                  strip=["script", "style"],
                  newline_style="backslash",
                  bullets="-").strip()
        if text:
            result.append(("text", text))
        pending_html.clear()

    # 递归提取所有 img，把其余内容保持结构
    def walk(nodes):
        for node in nodes:
            tag = getattr(node, "name", None)

            if tag == "img":
                flush_pending()
                src = node.get("src") or node.get("data-src") or node.get("data-original") or ""
                src = src.strip()
                if src and src.startswith("http"):
                    result.append(("image", src))

            elif tag in (None,):
                # NavigableString（纯文本节点），归入 pending
                text = str(node).strip()
                if text:
                    pending_html.append(node)

            else:
                # 检查子节点里有没有 img
                inner_imgs = node.find_all("img")
                if not inner_imgs:
                    # 没有图片，整块转 Markdown
                    pending_html.append(node)
                else:
                    # 有图片，拆开子节点处理
                    flush_pending()
                    walk(node.children)

    walk(soup.children)
    flush_pending()
    return result


# ─────────────────────────────────────────────
# Markdown → Notion Blocks
# ─────────────────────────────────────────────
def _rich_text(
    content: str,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
    strikethrough: bool = False,
    href: Optional[str] = None,
) -> dict:
    obj = {
        "type": "text",
        "text": {"content": content[:2000]},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "code": code,
            "strikethrough": strikethrough,
            "underline": False,
            "color": "default",
        },
    }
    if href:
        obj["text"]["link"] = {"url": href}
    return obj


def _inline_to_rich_text(node: dict) -> list[dict]:
    t = node.get("type", "")
    children = node.get("children", [])

    if t == "RawText":
        return [_rich_text(node.get("content", ""))]
    if t == "Strong":
        parts = []
        for child in children:
            for rt in _inline_to_rich_text(child):
                rt["annotations"]["bold"] = True
                parts.append(rt)
        return parts
    if t == "Emphasis":
        parts = []
        for child in children:
            for rt in _inline_to_rich_text(child):
                rt["annotations"]["italic"] = True
                parts.append(rt)
        return parts
    if t == "InlineCode":
        raw = children[0].get("content", "") if children else ""
        return [_rich_text(raw, code=True)]
    if t == "Strikethrough":
        parts = []
        for child in children:
            for rt in _inline_to_rich_text(child):
                rt["annotations"]["strikethrough"] = True
                parts.append(rt)
        return parts
    if t == "Link":
        href = node.get("target", "")
        parts = []
        for child in children:
            for rt in _inline_to_rich_text(child):
                rt["text"]["link"] = {"url": href}
                parts.append(rt)
        return parts
    if t == "Image":
        alt = "".join(c.get("content", "") for c in children)
        return [_rich_text(f"[图片: {alt}]")]
    parts = []
    for child in children:
        parts.extend(_inline_to_rich_text(child))
    return parts


def _collect_rich_text(children: list) -> list[dict]:
    result = []
    for child in children:
        result.extend(_inline_to_rich_text(child))
    return result or [_rich_text("")]


NOTION_CODE_LANGS = {
    "abap", "arduino", "bash", "basic", "c", "clojure", "coffeescript", "c++", "c#",
    "css", "dart", "diff", "docker", "elixir", "elm", "erlang", "flow", "fortran", "f#",
    "gherkin", "glsl", "go", "graphql", "groovy", "haskell", "html", "java", "javascript",
    "json", "julia", "kotlin", "latex", "less", "lisp", "livescript", "lua", "makefile",
    "markdown", "markup", "matlab", "mermaid", "nix", "objective-c", "ocaml", "pascal",
    "perl", "php", "plain text", "powershell", "prolog", "protobuf", "python", "r",
    "reason", "ruby", "rust", "sass", "scala", "scheme", "scss", "shell", "sql", "swift",
    "toml", "typescript", "vb.net", "verilog", "vhdl", "visual basic", "webassembly",
    "xml", "yaml", "java/c/c++/c#",
}


def _node_to_blocks(node: dict) -> list[dict]:
    t = node.get("type", "")
    children = node.get("children", [])
    blocks = []

    if t == "Document":
        for child in children:
            blocks.extend(_node_to_blocks(child))

    elif t == "Heading":
        level = min(node.get("level", 1), 3)
        ht = f"heading_{level}"
        blocks.append({"object": "block", "type": ht,
                        ht: {"rich_text": _collect_rich_text(children)}})

    elif t == "Paragraph":
        # 段落内 img（markdownify 产生的 ![alt](url)）也拆出来
        text_buf = []
        for child in children:
            if child.get("type") == "Image":
                if text_buf:
                    blocks.append({"object": "block", "type": "paragraph",
                                   "paragraph": {"rich_text": _collect_rich_text(text_buf)}})
                    text_buf = []
                src = child.get("target", "") or child.get("src", "")
                if src:
                    blocks.append({"object": "block", "type": "image",
                                   "image": {"type": "external", "external": {"url": src}}})
            else:
                text_buf.append(child)
        if text_buf:
            rt = _collect_rich_text(text_buf)
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": rt}})

    elif t in ("CodeFence", "BlockCode"):
        code_content = children[0].get("content", "") if children else ""
        lang = (node.get("language") or "plain text").strip().lower() or "plain text"
        if lang not in NOTION_CODE_LANGS:
            lang = "plain text"
        blocks.append({"object": "block", "type": "code",
                        "code": {"rich_text": [_rich_text(code_content[:2000])],
                                 "language": lang}})

    elif t == "List":
        ordered = node.get("start") is not None and node.get("start") is not False
        list_type = "numbered_list_item" if ordered else "bulleted_list_item"
        for item in children:
            ic = item.get("children", [])
            first = ic[0] if ic else {}
            rt = _collect_rich_text(first.get("children", []))
            block: dict = {"object": "block", "type": list_type,
                           list_type: {"rich_text": rt}}
            nested = [b for sub in ic[1:] for b in _node_to_blocks(sub)]
            if nested:
                block[list_type]["children"] = nested[:100]
            blocks.append(block)

    elif t == "Quote":
        rt = []
        for child in children:
            rt.extend(_collect_rich_text(child.get("children", [])))
        blocks.append({"object": "block", "type": "quote",
                        "quote": {"rich_text": rt or [_rich_text("")]}})

    elif t == "ThematicBreak":
        blocks.append({"object": "block", "type": "divider", "divider": {}})

    elif t == "Table":
        rows = []
        for row in children:
            cells = []
            for cell in row.get("children", []):
                text = "".join(
                    c.get("content", "")
                    for c in cell.get("children", [{}])[0].get("children", [])
                    if c.get("type") == "RawText"
                )
                cells.append(text)
            rows.append(" | ".join(cells))
        blocks.append({"object": "block", "type": "code",
                        "code": {"rich_text": [_rich_text("\n".join(rows))],
                                 "language": "plain text"}})

    return blocks


def markdown_to_notion_blocks(text: str) -> list[dict]:
    if not text.strip():
        return []
    with AstRenderer() as renderer:
        ast_str = renderer.render(Document(text))
    ast = json.loads(ast_str) if isinstance(ast_str, str) else ast_str
    return _node_to_blocks(ast)


def entry_to_notion_blocks(entry) -> list[dict]:
    """
    把 RSSEntry.blocks（文字+图片交替列表）转换为 Notion block 列表。
    ("text", md_str) → markdown_to_notion_blocks
    ("image", url)   → image block
    """
    result = []
    for kind, val in entry.blocks:
        if kind == "image":
            result.append({
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": val}},
            })
        elif kind == "text":
            result.extend(markdown_to_notion_blocks(val))
    return result
