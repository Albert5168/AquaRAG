import docx
import json
import re
import os
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
        # Convert multiple lines inside cell to blockquotes
        lines = [f"> {line}" for line in text.split('\n')]
        return "\n".join(lines) + "\n"
        
    markdown_lines = []
    
    # Process rows
    for r_idx, row in enumerate(rows):
        cells = row.cells
        row_text = []
        for cell in cells:
            # Strip and clean text in cell
            cell_text = cell.text.strip().replace('\n', '<br>')
            row_text.append(cell_text)
            
        markdown_lines.append("| " + " | ".join(row_text) + " |")
        
        # Add separator after header row
        if r_idx == 0:
            separator = "| " + " | ".join(["---"] * len(cells)) + " |"
            markdown_lines.append(separator)
            
    return "\n".join(markdown_lines) + "\n"

def parse_docx(file_path):
    print(f"Loading document: {file_path}")
    doc = docx.Document(file_path)
    
    questions = []
    current_exam_set = "未分類試題"
    current_question = None
    
    exam_set_pattern = re.compile(r'^第\s*(\d+)\s*套試題：(.*)$')
    question_pattern = re.compile(r'^第\s*(\d+)\s*題：(.*)$')
    
    element_count = 0
    
    for item in iter_block_items(doc):
        element_count += 1
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
                
            # Check for Exam Set header
            exam_match = exam_set_pattern.match(text)
            if exam_match:
                set_num = exam_match.group(1)
                set_name = exam_match.group(2).strip()
                current_exam_set = f"第 {set_num} 套試題：{set_name}"
                print(f"Found Exam Set: {current_exam_set}")
                continue
                
            # Check for Question header
            q_match = question_pattern.match(text)
            if q_match:
                q_num = q_match.group(1)
                q_title = q_match.group(2).strip()
                
                # Save previous question
                if current_question:
                    questions.append(current_question)
                    
                current_question = {
                    "id": len(questions) + 1,
                    "exam_set": current_exam_set,
                    "question_num": f"第 {q_num} 題",
                    "question_title": q_title,
                    "original_question": "",
                    "content_elements": [text]
                }
                continue
                
            # If we are inside a question block, add the text
            if current_question:
                current_question["content_elements"].append(text)
                
        elif isinstance(item, Table):
            if current_question:
                # Convert table to markdown
                tbl_md = table_to_markdown(item)
                # Check if this is the 1x1 table of original question
                if len(item.rows) == 1 and len(item.columns) == 1 and "【原題重現】" in item.rows[0].cells[0].text:
                    current_question["original_question"] = item.rows[0].cells[0].text.strip()
                
                current_question["content_elements"].append(tbl_md)
                
    # Save the last question
    if current_question:
        questions.append(current_question)
        
    # Process full content for each question
    for q in questions:
        q["full_content"] = "\n\n".join(q["content_elements"])
        # Clean up temporary storage
        del q["content_elements"]
        
    print(f"Total elements processed: {element_count}")
    print(f"Total questions parsed: {len(questions)}")
    return questions

if __name__ == "__main__":
    docx_path = "魚類生理學歷屆試題專家解答.docx"
    if not os.path.exists(docx_path):
        print(f"Error: {docx_path} not found.")
    else:
        parsed_data = parse_docx(docx_path)
        output_path = "parsed_questions.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        print(f"Saved parsed questions to {output_path}")
