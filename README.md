# Z.ai2api
将 Z.ai 代理为 OpenAI Compatible 格式，支持免 Cookie、智能处理思考链等功能  
基于 https://github.com/kbykb/OpenAI-Compatible-API-Proxy-for-Z 使用 AI 辅助重构。  

## 功能
- 支持根据官网 /api/models 生成模型列表，并自动选择合适的模型名称。
- 支持智能识别思考链，并完美转换为下列三种格式
  - "think"
    - 将 `<details>` 元素替换为 `<think>` 元素，并去除 Markdown 引用块（`>`）
    - `<think>\n\n> 嗯，用户……\n\n</think>\n\n你好！`
  - "pure"
    - 去除 `<details>` 标签
    - `> 嗯，用户……\n\n你好！`
  - "raw"
    - 重构为 `<details><div>` 标签，显示英文思考时间
    - `<details type="reasoning" open><div>\n\n嗯，用户……\n\n</div><summary>Thought for 1 seconds</summary></details>\n\n你好！`
## 使用
```
git clone https://github.com/hmjz100/Z.ai2api.git
cd Z.ai2api
pip install -r requirements.txt
python app.py
```
