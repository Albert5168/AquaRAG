import json
import os

def main():
    json_path = "parsed_questions.json"
    output_path = "train_dataset.jsonl"
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Running dataset preparation failed.")
        return
        
    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    print(f"Loaded {len(questions)} questions for training.")
    
    with open(output_path, "w", encoding="utf-8") as out_f:
        for idx, q in enumerate(questions):
            # Construct standard ChatML format for Qwen-2.5 Instruction Tuning
            message_struct = {
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是一個「魚類生理學」與國家考試解題專家 AI，請提供專業、條理分明且深入學術機制的解答。"
                    },
                    {
                        "role": "user", 
                        "content": f"這是 {q['exam_set']} 的 {q['question_num']}：\n{q['question_title']}\n\n請以學術與考試方向給出詳細專家解析。"
                    },
                    {
                        "role": "assistant", 
                        "content": q['full_content']
                    }
                ]
            }
            out_f.write(json.dumps(message_struct, ensure_ascii=False) + "\n")
            
    print(f"Successfully generated training dataset: {output_path} with {len(questions)} samples.")

if __name__ == "__main__":
    main()
