import json
import re

INPUT_FILE = "takagi_dataset.txt"
OUTPUT_FILE = "takagi_dataset_cleaned.txt"

def is_valid_dialogue(input_text, output_text):
    # 规则 1：过滤太短的废话（比如只有“啊”、“嗯”、“西片！”）
    if len(input_text) < 6 or len(output_text) < 6:
        return False
        
    # 规则 2：过滤西片的内心独白（通常带有括号）
    if "（" in input_text or "）" in input_text or "【" in input_text or "】" in input_text:
        return False
        
    # 规则 3：过滤残留的 ASS 字幕特效代码
    if "\\" in output_text or "{" in output_text or "}" in output_text:
        return False
        
    # 规则 4：过滤高木的非对话语气词（比如全是“哈哈哈”、“嘿嘿”）
    # 如果一句话里标点符号比字还多，大概率是无意义的
    if len(output_text) > 5 and len(re.findall(r'[。，！？、~…]', output_text)) > len(output_text) / 2:
        return False
        
    return True

def clean_data():
    valid_count = 0
    total_count = 0
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as fin, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as fout:
         
        for line in fin:
            if not line.strip():
                continue
            total_count += 1
            try:
                data = json.loads(line)
                inp = data.get("input", "")
                outp = data.get("output", "")
                
                if is_valid_dialogue(inp, outp):
                    fout.write(line)
                    valid_count += 1
            except json.JSONDecodeError:
                continue
                
    print(f"🧹 清洗完毕！总数据: {total_count} 条，保留有效数据: {valid_count} 条。")
    print(f"已被过滤掉 {(total_count - valid_count)} 条低质量数据。")

if __name__ == "__main__":
    clean_data()