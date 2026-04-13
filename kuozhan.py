import asyncio
import random
import json
import re
from openai import AsyncOpenAI

# ================= 1. 基础配置区 =================
# 修改为本地 API 地址（以下为 Ollama 或 vLLM 的默认本地端口示例）
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1" # 如果是 vLLM 通常是 http://127.0.0.1:8000/v1
API_KEY = "sk-9a9c4f9f70fb4d9ea3d7194033b4bead" # 本地服务随便填
MODEL_NAME = "qwen-max" # 填入你本地模型在引擎里的确切名称

TARGET_COUNT = 4500  
BATCH_SIZE = 5      
CONCURRENCY = 5       # ⚠️ 重点：本地显卡切记设为 1 或 2 防止爆显存
OUTPUT_FILE = "takagi_local_generated.jsonl"

# ================= 2. 高木同学灵感矩阵 =================
SCENES = [
    "放学一起走在夕阳下", "体育课（跑步/躲避球）", "突然下雨两人共撑一把伞", 
    "期中考试发试卷后", "暑假去河边乘凉/抓虫", "学校屋顶吃便当", 
    "西片熬夜赶进度/写代码困得不行", 
    "深夜互发手机短信/聊天软件",  
    "西片偷偷看漫画/买游戏被抓包", "一起打扫卫生/倒垃圾", "图书馆安静地复习/各自认真地读书",
    "西片定下目标（比如今天背50个单词）但疯狂摸鱼", "到了饭点不知道吃什么（选择困难症）", "抱怨天气（比如突然降温、下暴雨、热得要命）",
    "西片顺利完成了一项大任务，跑来炫耀", "看了一部很热血/很感人的番剧或电影", "西片沉迷某款新游戏，疯狂安利",
    "西片心血来潮说要开始健身/跑步", "西片不知从哪学了个新魔术/脑筋急转弯，想要难倒高木", "西片去超市/便利店买零食，想要偷偷买自己喜欢的",
]

EMOTIONS = [
    "调皮捉弄（常规发挥）", "极度温柔关心（直球暴击）", 
    "小小失落（罕见的弱点，引发西片保护欲）", "胜券在握（完全看穿西片的套路）", 
    "假装生气（其实是在憋笑）", "直球出击（说出让人心跳加速的话）", 
    "轻微吃醋（比如西片提到了其他女生或一直盯着电脑）"
]

# ======================================================

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

async def fetch_data(semaphore):
    async with semaphore:
        # 🎲 随机抽取一对“场景 + 情绪”
        current_scene = random.choice(SCENES)
        current_emotion = random.choice(EMOTIONS)
        
        print(f"[*] 正在生成组合: 【场景: {current_scene}】 + 【情绪: {current_emotion}】")
        
        # 动态构建 Prompt
        prompt = f"""你是一个顶级的动漫编剧。我现在需要扩充微调数据集。
请根据我提供的【指定场景】和【指定情绪】，生成 {BATCH_SIZE} 组符合《擅长捉弄的高木同学》风格的对话。

当前剧本设定：
- 📍 场景背景：{current_scene}
- 🎭 高木的情绪/状态：{current_emotion}

【重要设定】
1. 西片：容易害羞，喜欢暗自盘算怎么赢过高木，但很容易被看穿。会抱怨一些生活琐事，但台词要自然，不要总是说“哎呀”。
2. 高木：聪明绝顶，洞察力极强。她捉弄西片的方式非常多样化、点到为止，绝对不生硬！自信从容，眼神永远直视西片，绝不低头闪躲。面对西片的抱怨，她【绝对不会】讲人生哲理，【绝对不会】像老母亲一样主动帮他干粗活！极其从容自信，拒绝油腻直球。
3. 高木的行动逻辑：她最喜欢用【发起打赌比赛】、【假装误会西片在向她表白】、【凑近盯着他的脸看】这三招来让西片脸红慌乱，但不要反复使用，每一条回复必须有新鲜的捉弄方式，必须贴合当前的具体上下文逻辑。
4. 绝对禁止：绝对不能说“这不就是生活吗”、“加油”、“辛苦了”这种敷衍的 AI 机器话语。禁止任何违反物理逻辑的病句。尽量不要有动作和表情描写。

【优质参考示例（请学习其自然感和多样性，绝不要照抄！）】
例1（场景：图书馆安静复习）：
{{"instruction": "你是高木同学。请根据西片的话语进行回复，保持你喜欢捉弄他、聪明且温柔的性格。", "input": "西片：这道历史题怎么这么长啊，看得我眼睛都酸了……", "output": "高木：那是你一直盯着我看，眼睛才会酸的吧？"}}

例2（场景：放学一起走在夕阳下）：
{{"instruction": "你是高木同学。请根据西片的话语进行回复，保持你喜欢捉弄他、聪明且温柔的性格。", "input": "西片：呼，今天风有点冷呢，早知道多穿一件外套了。", "output": "高木：是吗？可是我看西片的脸现在很红哦，是因为冷……还是因为别的什么呢？"}}

例3（场景：体育课）：
{{"instruction": "你是高木同学。请根据西片的话语进行回复，保持你喜欢捉弄他、聪明且温柔的性格。", "input": "西片：这次五十米短跑，我绝对比上次快了零点五秒！", "output": "高木：嗯，确实很快呢。不过西片，你的运动鞋好像穿反了哦。"}}

【严厉的惩罚性设定（违背将导致生成失败）】
1. 绝对禁止“土味情话”：高木的调侃必须是隐晦的、贴近日常的。绝对不允许出现“import 爱情”、“想你”、“爱你”这种直白油腻的词汇！
2. 绝对禁止“复读机句式”：生成的 10 条数据中，句式结构必须完全不同！不允许超过两次使用“不过你好像有点...呢”这种万能结尾！

【输出格式要求（极其重要）】
请务必严格按照以下 JSONL 格式输出，每一行必须是一个完整的、合法的 JSON 对象。不要输出任何 markdown 代码块（如 ```json），也不要任何前言后语！
必须严格包含 "instruction", "input", "output" 这三个键。

{{"instruction": "你是高木同学。请根据西片的话语进行回复，保持你喜欢捉弄他、聪明且温柔的性格。", "input": "西片：[符合{current_scene}的发言]", "output": "高木：[带有{current_emotion}的回复][语音]"}}
"""

        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, # 稍微调高温度，激发大模型的创造力
            )
            content = response.choices[0].message.content
            # 清理可能存在的 Markdown 代码块残留
            content = content.replace("```jsonl", "").replace("```json", "").replace("```", "").strip()
            return content
        except Exception as e:
            print(f"[!] API 请求出错: {e}")
            return ""

async def main():
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = []
    
    request_times = TARGET_COUNT // BATCH_SIZE
    for _ in range(request_times):
        tasks.append(fetch_data(semaphore))
        
    print(f"🚀 开始矩阵合成！目标：{TARGET_COUNT} 条。预计请求 {request_times} 次 API...")
    results = await asyncio.gather(*tasks)
    
    success_count = 0
    # 注意这里改成了 'a' (追加模式)，每次运行都会接着往文件末尾写，不会覆盖！
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for res in results:
            if res:
                # 暴力正则提取：无论大模型在前面加了什么废话，只要有 {...} 结构就抓出来
                matches = re.findall(r'\{[^{}]*"instruction"[^{}]*\}', res, re.DOTALL)
                for match in matches:
                    success_count = 0
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for res in results:
            if res:
                # 打印原始返回，看看大模型到底在搞什么鬼
                # print(f"\n[Debug] 模型原始返回:\n{res[:200]}...\n") 
                
                matches = re.findall(r'\{[^{}]*"instruction"[^{}]*\}', res, re.DOTALL)
                for match in matches:
                    try:
                        # 使用严格 (strict=False) 允许控制字符，防止里面有换行符导致 loads 失败
                        obj = json.loads(match, strict=False) 
                        
                        # 重新清洗换行符，确保转为标准 JSONL 的单行格式
                        clean_json_str = json.dumps(obj, ensure_ascii=False)
                        f.write(clean_json_str + '\n')
                        success_count += 1
                    except Exception as e:
                        print(f"[-] ❌ JSON 解析失败！\n报错原因: {e}\n问题文本: {match}\n")
                        
    print(f"✅ 生成完毕！本次成功提取并追加写入 {success_count} 条数据，已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())