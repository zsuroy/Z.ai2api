<div align=center>
<img width="100" src="https://wsrv.nl/?url=https%3a%2f%2fz-cdn.chatglm.cn%2fz-ai%2fstatic%2flogo.svg&w=300&output=webp" />
<h1>Z.ai2api</h1>
<p>将 Z.ai 代理为 OpenAI Compatible 格式，支持免令牌、智能处理思考链、图片上传（登录后）等功能</p>
<p>基于 https://github.com/kbykb/OpenAI-Compatible-API-Proxy-for-Z 使用 AI 辅助重构</p>
</div>

## 功能
- 支持根据官网 /api/models 生成模型列表，并自动选择合适的模型名称。
- （登录后）支持上传图片，使用 GLM 识图系列模型。
- 支持智能识别思考链，完美转换多种格式。

## 要求
![Python 3.12+](https://img.shields.io/badge/3.12%2B-blue?style=for-the-badge&logo=python&label=python)
![.env](https://img.shields.io/badge/.env-%23555?style=for-the-badge&logo=.env)

## 环境
使用 `.env` 文件进行配置。
### `BASE`
  - 上游 API 基础域名
  - 默认值：`https://chat.z.ai`
### `PORT`
  - 服务端口
  - 默认值：`8080`
### `MODEL`
  - 备选模型，在未传入模型时调用
  - 默认值：`GLM-4.5`
### `TOKEN`
  - 访问令牌
  - 如果启用了 `ANONYMOUS_MODE` 可不填
### `ANONYMOUS_MODE`
  - 访客模式，启用后将获取随机令牌
  - 默认值：`true`
  - 访客模式下不支持上传文件调用视觉模型
### `THINK_TAGS_MODE`
  - 思考链格式化模式
  - 默认值：`reasoning`
  - 可选 `reasoning` `think` `strip` `details`，效果如下
    - "reasoning"
      - reasoning_content: `嗯，用户……`
      - content: `你好！`
    - "think"
      - content: `<think>\n\n嗯，用户……\n\n</think>\n\n你好！`
    - "strip"
      - content: `> 嗯，用户……\n\n你好！`
    - "details"
      - content: `<details type="reasoning" open><div>\n\n嗯，用户……\n\n</div><summary>Thought for 1 seconds</summary></details>\n\n你好！`
### `DEBUG_MODE`
  - 显示调试信息，启用后将显示一些调试信息
  - 默认值：`false`

## 使用
```
git clone https://github.com/zsuroy/Z.ai2api.git
cd Z.ai2api
pip install -r requirements.txt
python app.py
```

## Docker 部署

### 构建镜像
```bash
docker build -t zai2api .
```

### 运行容器
```bash
docker run -d \
  --name zai2api \
  -p 8080:8080 \
  -e BASE=https://chat.z.ai \
  -e PORT=8080 \
  -e MODEL=GLM-4.5 \
  -e TOKEN=your_token_here \
  -e ANONYMOUS_MODE=true \
  -e THINK_TAGS_MODE=reasoning \
  -e DEBUG=false \
  zai2api
```

### 环境变量说明
所有环境变量与本地部署相同：
- `BASE`: 上游 API 基础域名
- `PORT`: 服务端口
- `MODEL`: 备选模型
- `TOKEN`: 访问令牌
- `ANONYMOUS_MODE`: 访客模式
- `THINK_TAGS_MODE`: 思考链格式化模式
- `DEBUG`: 调试模式

### 使用 Docker Compose (可选)

1. 开发构建镜像(可选)
创建 `docker-compose.yml` 文件：
```yaml
version: '3.8'
services:
  zai2api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - BASE=https://chat.z.ai
      - PORT=8080
      - MODEL=GLM-4.5
      - TOKEN=
      - ANONYMOUS_MODE=true
      - THINK_TAGS_MODE=reasoning
      - DEBUG=false
    volumes:
      - .env:/app/.env
```

2. 直接在项目目录下运行
```bash
docker-compose up -d
```
