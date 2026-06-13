import os
import sys
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

def main():
    model_id = "Qwen/Qwen2.5-7B-Instruct"  # 可依硬體改為 "Qwen/Qwen2.5-1.5B-Instruct"
    dataset_path = "train_dataset.jsonl"
    output_dir = "./qwen2.5_lora_output"
    
    if not os.path.exists(dataset_path):
        print(f"Error: dataset {dataset_path} not found. Run prepare_dataset.py first.")
        sys.exit(1)
        
    print(f"Loading tokenizer from {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # 1. 載入資料集
    print(f"Loading dataset {dataset_path}...")
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    
    # 2. QLoRA 4-bit 壓縮載入配置 (以節省 GPU 顯示記憶體)
    print("Configuring QLoRA 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    # 3. 載入預訓練模型
    print(f"Loading model {model_id} in 4-bit...")
    device_map = "auto"
    # 如果是 Mac (MPS) 或沒有 GPU 的環境，微調通常不支援 nf4 量化，需作降級判斷
    if not torch.cuda.is_available():
        print("WARNING: CUDA is not available. Running on CPU/MPS without 4-bit quantization.")
        bnb_config = None
        device_map = "cpu"
        
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True
    )
    
    # 4. 準備 K-bit 訓練與 LoRA 設定
    if torch.cuda.is_available():
        model = prepare_model_for_kbit_training(model)
        
    print("Configuring LoRA Adapter...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # 5. 設定訓練超參數
    print("Setting up training arguments...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        num_train_epochs=3,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        fp16=True if torch.cuda.is_available() else False,
        save_strategy="epoch",
        report_to="none"  # 不上傳 WandB 等日誌系統
    )
    
    # 6. 使用 SFTTrainer 進行對話格式訓練
    print("Starting SFTTrainer initialization...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="messages",  # 配合 Hugging Face TRL 讀取聊天格式
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=training_args,
    )
    
    # 7. 開始微調
    print("🚀 Starting training loop...")
    trainer.train()
    
    # 8. 儲存 Adapter
    adapter_dir = "./qwen2.5_lora_adapter"
    print(f"Saving LoRA adapter to {adapter_dir}...")
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print("🎉 Fine-tuning completed successfully!")

if __name__ == "__main__":
    main()
