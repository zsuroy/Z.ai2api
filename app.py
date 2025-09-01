# -*- coding: utf-8 -*-
"""
Z.ai 2 API
将 Z.ai 代理为 OpenAI Compatible 格式，支持免 Cookie、智能处理思考链等功能
基于 https://github.com/kbykb/OpenAI-Compatible-API-Proxy-for-Z 使用 AI 辅助重构。
"""

import json, re, requests, logging
from datetime import datetime
from flask import Flask, request, Response, jsonify, make_response

# --- 配置 ---
API_BASE = "https://chat.z.ai"
PORT = 8080 # 对外端口
UPSTREAM_TOKEN = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjMxNmJjYjQ4LWZmMmYtNGExNS04NTNkLWYyYTI5YjY3ZmYwZiIsImVtYWlsIjoiR3Vlc3QtMTc1NTg0ODU4ODc4OEBndWVzdC5jb20ifQ.PktllDySS3trlyuFpTeIZf-7hl8Qu1qYF3BxjgIul0BrNux2nX9hVzIjthLXKMWAf9V0qM8Vm_iyDqkjPGsaiQ"
MODEL_NAME = "GLM-4.5" # 没传入模型时选用的默认模型
DEBUG_MODE = True # 显示调试信息
THINK_TAGS_MODE = "pure" # 思考链处理，选项说明详见 https://github.com/hmjz100/Z.ai2api/blob/main/README.md#%E5%8A%9F%E8%83%BD
ANON_TOKEN_ENABLED = True # 是否启用访客模式（即不调用 UPSTREAM_TOKEN）

BROWSER_HEADERS = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/139.0.0.0",
	"Accept": "*/*",
	"Accept-Language": "zh-CN,zh;q=0.9",
	"X-FE-Version": "prod-fe-1.0.76",
	"sec-ch-ua": '"Not;A=Brand";v="99", "Edge";v="139"',
	"sec-ch-ua-mobile": "?0",
	"sec-ch-ua-platform": '"Windows"',
	"Origin": API_BASE,
}

# --- 日志 ---
logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO,
					format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

def debug(msg, *args): 
	if DEBUG_MODE: log.debug(msg, *args)

# --- Flask 应用 ---
app = Flask(__name__)

# --- 工具函数 ---
def set_cors(resp):
	resp.headers.update({
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "GET, POST, OPTIONS",
		"Access-Control-Allow-Headers": "Content-Type, Authorization",
	})
	return resp

def new_id(prefix="msg"): return f"{prefix}-{int(datetime.now().timestamp()*1e9)}"

history_phase = "thinking"
def process_content(content: str, phase: str) -> str:
	global history_phase
	history_content = content
	if content and (phase == "thinking" or "summary>" in content):
		content = re.sub(r"(?s)<details[^>]*?>.*?</details>", "", content)
		content = content.replace("</thinking>", "").replace("<Full>", "").replace("</Full>", "")
		if THINK_TAGS_MODE == "think":
			if phase == "thinking":
				content = content.lstrip("> ").replace("\n>", "\n").strip()

			content = re.sub(r'\n?<summary>.*?</summary>\n?', '', content)
			content = re.sub(r"<details[^>]*>\n?", "<think>\n\n", content)
			content = re.sub(r"\n?</details>", "\n\n</think>", content)
			if phase == "answer":
				# 判断 </think> 后是否有内容
				match = re.search(r"(?s)^(.*?</think>)(.*)$", content)
				if match:
					before, after = match.groups()
					if after.strip():
						# 回答休止：</think> 后有内容
						if history_phase == "thinking":
							# 上条是思考 → 结束思考，加上回答
							content = f"\n\n</think>{after}"
						elif history_phase == "answer":
							# 上条是回答 → 清除所有
							content = ""
					else:
						# 思考休止：</think> 后没有内容 → 保留一个 </think>
						content = "\n\n</think>"
		elif THINK_TAGS_MODE == "pure":
			if phase == "thinking":
				content = re.sub(r'\n?<summary>.*?</summary>', '', content)

			content = re.sub(r"<details[^>]*>\n?", "<details type=\"reasoning\">\n\n", content)
			content = re.sub(r"\n?</details>", "\n\n></details>", content)

			if phase == "answer":
				# 判断 </details> 后是否有内容
				match = re.search(r"(?s)^(.*?</details>)(.*)$", content)
				if match:
					before, after = match.groups()
					if after.strip():
						# 回答休止：</think> 后有内容
						if history_phase == "thinking":
							# 上条是思考 → 结束思考，加上回答
							content = f"\n\n{after}"
						elif history_phase == "answer":
							# 上条是回答 → 清除所有
							content = ""
					else:
						content = "\n\n"
			content = re.sub(r"</?details[^>]*>", "", content)
		elif THINK_TAGS_MODE == "raw":
			if phase == "thinking":
				content = re.sub(r'\n?<summary>.*?</summary>', '', content)

			content = re.sub(r"<details[^>]*>\n?", "<details type=\"reasoning\" open><div>\n\n", content)
			content = re.sub(r"\n?</details>", "\n\n</div></details>", content)

			if phase == "answer":
				# 判断 </details> 后是否有内容
				match = re.search(r"(?s)^(.*?</details>)(.*)$", content)
				if match:
					before, after = match.groups()
					if after.strip():
						# 回答休止：</think> 后有内容
						if history_phase == "thinking":
							# 上条是思考 → 结束思考，加上回答
							content = f"\n\n</details>{after}"
						elif history_phase == "answer":
							# 上条是回答 → 清除所有
							content = ""
					else:
						# 思考休止: </details> 后没有内容 → 加入 summary + </details>
						summary_match = re.search(r"(?s)<summary>.*?</summary>", before)
						duration_match = re.search(r'duration="(\d+)"', before)

						if summary_match:
							content = f"\n\n</div>{summary_match.group()}</details>\n\n"
						elif duration_match:
							duration = duration_match.group(1)
							content = f'\n\n</div><summary>Thought for {duration} seconds</summary></details>\n\n'
						else:
							content = "\n\n</div></details>"

	if repr(content) != repr(history_content):
		debug("R 内容: %s %s", phase, repr(history_content))
		debug("W 内容: %s %s", phase, repr(content))
	else:
		debug("R 内容: %s %s", phase, repr(history_content))
	history_phase = phase
	return content
	

def get_token() -> str:
	if not ANON_TOKEN_ENABLED: return UPSTREAM_TOKEN
	try:
		r = requests.get(f"{API_BASE}/api/v1/auths/", headers=BROWSER_HEADERS, timeout=8)
		token = r.json().get("token")
		if token: 
			debug("获取匿名 token: %s...", token[:10])
			return token
	except Exception as e:
		debug("匿名 token 获取失败: %s", e)
	return UPSTREAM_TOKEN

def call_upstream(data, chat_id):
	headers = {**BROWSER_HEADERS, "Authorization": f"Bearer {get_token()}", "Referer": f"{API_BASE}/c/{chat_id}"}
	debug("上游请求: %s", json.dumps(data, ensure_ascii=False))
	return requests.post(f"{API_BASE}/api/chat/completions", json=data, headers=headers, stream=True, timeout=60)

def parse_upstream(upstream):
	"""统一 SSE 解析生成器"""
	for line in upstream.iter_lines():
		if not line or not line.startswith(b"data: "): continue
		try: data = json.loads(line[6:].decode("utf-8", "ignore"))
		except: continue
		yield data

def extract_content(data):
	phase, delta, edit = data.get("data", {}).get("phase"), data.get("data", {}).get("delta_content",""), data.get("data",{}).get("edit_content","")
	content = delta or edit
	if content and (phase == "answer" or phase == "thinking"):
		return process_content(content, phase) or ""
	return content or ""

# --- 路由 ---
@app.route("/v1/models", methods=["GET", "OPTIONS"])
def models():
	if request.method=="OPTIONS": return set_cors(make_response())
	try:
		def format_model_name(name: str) -> str:
			"""格式化模型名:
			- 单段: 全大写
			- 多段: 第一段全大写, 后续段首字母大写
			- 数字保持不变, 符号原样保留
			"""
			if not name: return ""
			parts = name.split('-')
			if len(parts) == 1:
				return parts[0].upper()
			formatted = [parts[0].upper()]
			for p in parts[1:]:
				if not p:
					formatted.append("")
				elif p.isdigit():
					formatted.append(p)
				elif any(c.isalpha() for c in p):
					formatted.append(p.capitalize())
				else:
					formatted.append(p)
			return "-".join(formatted)
		
		def is_english_letter(ch: str) -> bool:
			"""判断是否是英文字符 (A-Z / a-z)"""
			return 'A' <= ch <= 'Z' or 'a' <= ch <= 'z'

		headers = {**BROWSER_HEADERS, "Authorization": f"Bearer {get_token()}"}
		r = requests.get(f"{API_BASE}/api/models", headers=headers, timeout=8).json()
		models = []
		for m in r.get("data", []):
			if not m.get("info", {}).get("is_active", True):
				continue
			model_id, model_name = m.get("id"), m.get("name")
			# 使用规则格式化
			if model_id.startswith(("GLM", "Z")):
				model_name = model_id
			if not model_name or not is_english_letter(model_name[0]):
				model_name = format_model_name(model_id)
			models.append({
				"id": model_id,
				"object": "model",
				"name": model_name,
				"created": m.get("info", {}).get("created_at", int(datetime.now().timestamp())),
				"owned_by": "z.ai"
			})
		return set_cors(jsonify({"object":"list","data":models}))
	except Exception as e:
		debug("模型列表失败: %s", e)
		return set_cors(jsonify({"error":"fetch models failed"})), 500

@app.route("/v1/chat/completions", methods=["POST", "OPTIONS"])
def chat():
	if request.method=="OPTIONS": return set_cors(make_response())
	req = request.get_json(force=True, silent=True) or {}
	chat_id, msg_id, model = new_id("chat"), new_id("msg"), req.get("model", MODEL_NAME)
	upstream_data = {
		"stream": req.get("stream", False),
		"chat_id": chat_id, "id": msg_id,
		"model": model,
		"messages": req.get("messages", []),
		"features": {"enable_thinking": True},
	}
	try:
		upstream = call_upstream(upstream_data, chat_id)
	except Exception as e:
		return set_cors(make_response(f"上游调用失败: {e}", 502))
	
	if req.get("stream", False):
		def stream():
			yield f"data: {json.dumps({'id':new_id('chatcmpl'),'object':'chat.completion.chunk','model':model,'choices':[{'index':0,'delta':{'role':'assistant'}}]},ensure_ascii=False)}\n\n"
			for data in parse_upstream(upstream):
				if data.get("data",{}).get("done"): break
				content = extract_content(data)
				if content: yield f"data: {json.dumps({'id':new_id('chatcmpl'),'object':'chat.completion.chunk','model':model,'choices':[{'index':0,'delta':{'content':content}}]},ensure_ascii=False)}\n\n"
			yield "data: [DONE]\n\n"
		return Response(stream(), mimetype="text/event-stream")
	else:
		content = "".join(extract_content(d) for d in parse_upstream(upstream))
		resp = {"id":new_id("chatcmpl"),"object":"chat.completion","model":model,
				"choices":[{"index":0,"message":{"role":"assistant","content":content},"finish_reason":"stop"}],
				"usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0}}
		return set_cors(jsonify(resp))

# --- 主入口 ---
if __name__ == "__main__":
	log.info("代理启动: 端口=%s, 备选模型=%s，思考处理=%s, Debug=%s", PORT, MODEL_NAME, THINK_TAGS_MODE, DEBUG_MODE)
	app.run(host="0.0.0.0", port=PORT, threaded=True)
	# app.run(host="0.0.0.0", port=PORT, threaded=True, debug=True)
