import os
import sys
import re
import json
import docx
import zhconv
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table, _Cell

def iter_block_items(parent):
    """
    Yield each paragraph and table child within `parent`, in document order.
    """
    from docx.document import Document
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise TypeError("Unknown parent type")

    for child in parent_elm.iterchildren():
        if child.tag.endswith('p'):
            yield Paragraph(child, parent)
        elif child.tag.endswith('tbl'):
            yield Table(child, parent)

def table_to_markdown(table):
    """
    Convert a python-docx table to a markdown table string.
    """
    rows = table.rows
    if not rows:
        return ""
    
    # Check if table is 1x1
    if len(rows) == 1 and len(table.columns) == 1:
        text = rows[0].cells[0].text.strip()
        lines = [f"> {line}" for line in text.split('\n')]
        return "\n".join(lines) + "\n"
        
    markdown_lines = []
    for r_idx, row in enumerate(rows):
        cells = row.cells
        row_text = []
        for cell in cells:
            cell_text = cell.text.strip().replace('\n', '<br>')
            row_text.append(cell_text)
            
        markdown_lines.append("| " + " | ".join(row_text) + " |")
        
        if r_idx == 0:
            separator = "| " + " | ".join(["---"] * len(cells)) + " |"
            markdown_lines.append(separator)
            
    return "\n".join(markdown_lines) + "\n"

def is_heading(paragraph):
    """
    Detect if a paragraph functions as a heading based on style name or formatting.
    """
    style_name = paragraph.style.name.lower() if paragraph.style else ""
    if "heading" in style_name or "title" in style_name:
        return True
    
    text = paragraph.text.strip()
    if not text:
        return False
        
    # Check for bullet or number patterns that look like section titles (e.g. "一、前言", "1. 系統架構")
    # under 60 characters and no ending punctuation like period, comma, question mark.
    if len(text) < 60 and not text.endswith(('.', '。', ',', '，', '?', '？', '!', '！', ':', '：')):
        # Common Chinese heading patterns
        if re.match(r'^(?:第[一二三四五六七八九十百]+[章節回]|[0-9]+[\.\u3002]|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]\u3001)', text):
            return True
            
    return False

def parse_docx_to_chunks(file_path, target_chunk_size=700, overlap_size=150):
    """
    Parses a single docx file and chunks its contents logically.
    """
    print(f"Parsing document: {file_path}")
    doc = docx.Document(file_path)
    file_basename = os.path.basename(file_path)
    
    chunks = []
    current_heading = "前言"
    
    # We will accumulate items (paragraphs and markdown tables)
    text_buffer = []
    current_char_count = 0
    
    for item in iter_block_items(doc):
        if isinstance(item, Paragraph):
            text = zhconv.convert(item.text.strip(), 'zh-tw')
            if not text:
                continue
                
            # If we hit a new heading, we should cut the current chunk and start a new one
            if is_heading(item):
                if text_buffer:
                    chunk_text = "\n\n".join(text_buffer)
                    chunks.append({
                        "source_file": file_basename,
                        "chunk_title": current_heading,
                        "content": chunk_text
                    })
                    text_buffer = []
                    current_char_count = 0
                
                # Update current heading
                current_heading = text
                continue
            
            # If adding this paragraph exceeds target chunk size, cut the chunk
            if current_char_count > 0 and current_char_count + len(text) > target_chunk_size:
                chunk_text = "\n\n".join(text_buffer)
                chunks.append({
                    "source_file": file_basename,
                    "chunk_title": current_heading,
                    "content": chunk_text
                })
                
                # Keep some overlap paragraphs (e.g. last 1 or 2 paragraphs if length matches)
                overlap_buffer = []
                overlap_chars = 0
                for old_p in reversed(text_buffer):
                    if overlap_chars + len(old_p) < overlap_size:
                        overlap_buffer.insert(0, old_p)
                        overlap_chars += len(old_p)
                    else:
                        break
                
                text_buffer = overlap_buffer
                current_char_count = sum(len(p) for p in text_buffer)
            
            text_buffer.append(text)
            current_char_count += len(text)
            
        elif isinstance(item, Table):
            tbl_md = zhconv.convert(table_to_markdown(item), 'zh-tw')
            if not tbl_md:
                continue
                
            # If table is large, or if adding it exceeds size, cut the chunk first
            if current_char_count > 0 and current_char_count + len(tbl_md) > target_chunk_size:
                chunk_text = "\n\n".join(text_buffer)
                chunks.append({
                    "source_file": file_basename,
                    "chunk_title": current_heading,
                    "content": chunk_text
                })
                text_buffer = []
                current_char_count = 0
                
            text_buffer.append(tbl_md)
            current_char_count += len(tbl_md)
            
    # Add the remaining buffer
    if text_buffer:
        chunk_text = "\n\n".join(text_buffer)
        chunks.append({
            "source_file": file_basename,
            "chunk_title": current_heading,
            "content": chunk_text
        })
        
    print(f"Generated {len(chunks)} chunks for {file_basename}")
    return chunks

def main():
    docs_dir = "webpage_docs"
    output_path = "parsed_multi_docs.json"
    
    if not os.path.exists(docs_dir):
        print(f"Error: Directory '{docs_dir}' does not exist.")
        sys.exit(1)
        
    all_chunks = []
    chunk_counter = 1
    
    # Process all docx files in alphabetical order for consistency
    files = sorted([f for f in os.listdir(docs_dir) if f.endswith(".docx")])
    if not files:
        print(f"Warning: No .docx files found in '{docs_dir}' directory.")
        
    for file in files:
        file_path = os.path.join(docs_dir, file)
        try:
            chunks = parse_docx_to_chunks(file_path)
            for chunk in chunks:
                chunk["id"] = chunk_counter
                all_chunks.append(chunk)
                chunk_counter += 1
        except Exception as e:
            print(f"Error parsing file {file}: {e}")
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
    print(f"\nSuccessfully parsed all documents! Total chunks: {len(all_chunks)}")
    print(f"Saved parsed structured documents to {output_path}")

if __name__ == "__main__":
    main()
