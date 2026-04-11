"""
Word Engine - Renderer Module (Phase 1)
Renders normalized markdown to docx using python-docx and markdown-it-py.
"""
from docx import Document
from markdown_it import MarkdownIt
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def _apply_heading_style(run, level, params):
    """Apply basic heading styles from params if available."""
    # Stub styling logic for Phase 1 basic
    run.font.bold = True
    if level == 1:
        run.font.size = Pt(18)
    elif level == 2:
        run.font.size = Pt(16)
    else:
        run.font.size = Pt(14)

def _render_tokens(doc, tokens, params):
    """Walk through markdown-it tokens and render to docx."""
    list_level = 0
    in_list = False
    list_type = "bullet"  # 'bullet' or 'ordered'
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # ── Headings ──
        if token.type == "heading_open":
            level = int(token.tag[1:])  # e.g., 'h2' -> 2
            # Find the inline content
            i += 1
            content = ""
            while i < len(tokens) and tokens[i].type != "heading_close":
                if tokens[i].type == "inline":
                    content = tokens[i].content
                i += 1
            if level <= 3:
                # Add heading paragraph
                p = doc.add_paragraph()
                p.style = doc.styles[f"Heading {level}"]
                run = p.add_run(content)
                _apply_heading_style(run, level, params)
            
        # ── Paragraphs ──
        elif token.type == "paragraph_open":
            # Don't add normal paragraphs if we are inside a list (list item handles it)
            if not in_list:
                i += 1
                content = ""
                while i < len(tokens) and tokens[i].type != "paragraph_close":
                    if tokens[i].type == "inline":
                        content = tokens[i].content
                    i += 1
                p = doc.add_paragraph(content)
                
        # ── Lists ──
        elif token.type == "bullet_list_open":
            in_list = True
            list_type = "bullet"
            list_level += 1
        elif token.type == "bullet_list_close":
            list_level -= 1
            if list_level == 0:
                in_list = False
                
        elif token.type == "ordered_list_open":
            in_list = True
            list_type = "ordered"
            list_level += 1
        elif token.type == "ordered_list_close":
            list_level -= 1
            if list_level == 0:
                in_list = False
                
        elif token.type == "list_item_open":
            i += 1
            content = ""
            # Gather content until list_item_close
            while i < len(tokens) and tokens[i].type != "list_item_close":
                if tokens[i].type == "inline":
                    content = tokens[i].content
                i += 1
            
            style = 'List Bullet' if list_type == "bullet" else 'List Number'
            # Adjust style for nested lists if needed (python-docx has List Bullet 2, etc.)
            if list_level > 1:
                style += f" {list_level}"
                # Fallback to basic if nested style doesn't exist
                if style not in doc.styles:
                    style = 'List Bullet' if list_type == "bullet" else 'List Number'
                    
            doc.add_paragraph(content, style=style)
            
        # ── Code Blocks ──
        elif token.type == "fence":
            content = token.content
            # Remove trailing newline from code block if exists
            if content.endswith("\n"):
                content = content[:-1]
                
            p = doc.add_paragraph()
            try:
                p.style = doc.styles['Macro Text']
            except KeyError:
                p.style = doc.styles['Normal']
            run = p.add_run(content)
            run.font.name = "Courier New"
            # Simulate a basic block by indenting
            p.paragraph_format.left_indent = Inches(0.5)
            
        i += 1


def render_docx(md_text, params, output_path):
    """
    Render normalized markdown text to a docx file.
    
    Args:
        md_text: Normalized markdown string
        params: Parsed params.yaml dict
        output_path: Destination path for the .docx file
        
    Returns:
        output_path
    """
    doc = Document()
    md = MarkdownIt()
    
    tokens = md.parse(md_text)
    _render_tokens(doc, tokens, params)
    
    doc.save(output_path)
    return output_path
