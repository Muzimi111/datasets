import os
import re
import json
import pysubs2

# ================= 配置区 =================
SUBTITLE_DIR = "./subtitles"  # 把你的 srt 和 ass 文件都放到这个文件夹里
OUTPUT_FILE = "takagi_dataset.jsonl" # 输出的微调数据集文件
# ==========================================

def clean_text(text):
    """清洗字幕中的特效标签和换行符"""
    # 去除 ASS 特效标签 (形如 {\pos(400,300)} 等)
    text = re.sub(r'\{.*?\}', '', text)
    # 替换字幕换行符为空格
    text = text.replace('\\N', ' ').replace('\\n', ' ')
    # 去除首尾空格
    return text.strip()

def build_dataset():
    if not os.path.exists(SUBTITLE_DIR):
        print(f"请先创建 {SUBTITLE_DIR} 文件夹，并放入字幕文件！")
        return

    dataset = []
    
    # 遍历文件夹下的所有字幕文件
    for filename in os.listdir(SUBTITLE_DIR):
        if not filename.endswith(('.ass', '.srt')):
            continue
            
        filepath = os.path.join(SUBTITLE_DIR, filename)
        print(f"正在开采: {filename} ...")
        
        try:
            subs = pysubs2.load(filepath)
        except Exception as e:
            print(f"读取 {filename} 失败: {e}")
            continue

        # 提取当前集的所有纯净台词
        lines = [clean_text(line.text) for line in subs if clean_text(line.text)]

        # 核心逻辑：前后文配对与说话人推断
        for i in range(len(lines) - 1):
            line_a = lines[i]
            line_b = lines[i+1]
            
            is_takagi_speaking = False
            
            # 规则 1：高木经常叫西片的名字，如果后一句有“西片”，极大概率是高木说的
            if "西片" in line_b:
                is_takagi_speaking = True
                
            # 规则 2：西片经常叫高木同学，如果前一句有“高木”，后一句大概率是高木的回应
            if "高木" in line_a:
                is_takagi_speaking = True
                
            # 规则 3：过滤掉太短的语气词，或者明显是内心独白的场景
            if len(line_b) < 2 or "【" in line_b or "】" in line_b:
                is_takagi_speaking = False

            if is_takagi_speaking:
                # 构建 LLaMA-Factory 标准格式
                data_point = {
                    "instruction": "你是高木同学。请根据西片的话语进行回复，保持你喜欢捉弄他、聪明且温柔的性格。",
                    "input": f"西片：{line_a}",
                    "output": f"高木：{line_b}"
                }
                dataset.append(data_point)

    # 导出为 JSONL 文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"\n🎉 提取完成！共生成 {len(dataset)} 条高质量语料。")
    print(f"文件已保存为: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dataset()