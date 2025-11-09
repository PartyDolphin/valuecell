# ValueCell 项目运行指南

本文档详细说明 ValueCell 项目的架构、各子项目的作用、运行方式以及它们之间的协作关系。

## 项目架构概览

ValueCell 是一个多代理金融应用平台，采用前后端分离架构，包含以下主要组件：

```
┌─────────────────┐
│   前端 (UI)     │  React + TypeScript + Vite
│   Port: 1420    │
└────────┬────────┘
         │ HTTP REST API + SSE
         ▼
┌─────────────────┐
│   后端 (API)    │  FastAPI (Python)
│   Port: 8000    │
└────────┬────────┘
         │ A2A Protocol (HTTP)
         ▼
┌─────────────────────────────────────┐
│         代理服务 (Agents)           │
│  ┌──────────┐  ┌──────────┐         │
│  │ Research │  │ Trading │  ...    │
│  │  Agent   │  │  Agent  │         │
│  └──────────┘  └──────────┘         │
└─────────────────────────────────────┘
```

## 子项目说明

### 1. 前端 (frontend/)

**位置**: `/frontend/`

**技术栈**:
- React 19
- TypeScript
- Vite (构建工具)
- React Router (路由)
- Tailwind CSS (样式)
- Tauri (可选桌面应用)

**作用**:
- 提供用户交互界面
- 通过 HTTP REST API 与后端通信
- 通过 SSE (Server-Sent Events) 接收实时流式响应
- 管理对话历史、代理列表、设置等

**运行端口**: `1420`

**主要功能模块**:
- 代理聊天界面 (`/agent/*`)
- 首页 (`/home`)
- 市场 (`/market`)
- 设置 (`/setting`)
- 股票数据展示 (`/stock`)

### 2. 后端服务 (python/valuecell/server/)

**位置**: `/python/valuecell/server/`

**技术栈**:
- Python 3.12+
- FastAPI (Web 框架)
- SQLite (数据库)
- Uvicorn (ASGI 服务器)

**作用**:
- 提供 RESTful API 接口
- 管理对话、任务、用户配置
- 协调多个代理服务
- 处理 SSE 流式响应
- 管理数据库和持久化存储

**运行端口**: `8000`

**主要 API 路由**:
- `/api/v1/agents/*` - 代理相关接口
- `/api/v1/agents/stream` - SSE 流式接口
- `/api/v1/conversations/*` - 对话管理
- `/api/v1/tasks/*` - 任务管理
- `/api/v1/strategies/*` - 策略管理
- `/api/v1/models/*` - 模型配置
- `/api/v1/watchlist/*` - 关注列表

### 3. 代理服务 (python/valuecell/agents/)

**位置**: `/python/valuecell/agents/`

**技术栈**:
- Python 3.12+
- A2A Protocol (Agent-to-Agent 通信协议)
- 各种 LLM 模型集成

**作用**:
- 每个代理是独立的服务，提供特定领域的 AI 能力
- 通过 A2A 协议与后端通信
- 处理用户查询并返回结构化响应

**主要代理**:

#### 3.1 ResearchAgent (研究代理)
- **位置**: `/python/valuecell/agents/research_agent/`
- **功能**: 自动检索和分析基本面文档，生成数据洞察和可解释的摘要
- **启动命令**: `uv run -m valuecell.agents.research_agent`
- **端口**: 自动分配

#### 3.2 AutoTradingAgent (自动交易代理)
- **位置**: `/python/valuecell/agents/auto_trading_agent/`
- **功能**: 支持多种加密资产和 AI 驱动的交易策略，基于技术指标创建自动化交易
- **启动命令**: `uv run -m valuecell.agents.auto_trading_agent`
- **端口**: 自动分配
- **特殊配置**: 需要配置交易所 API 密钥（如 OKX）

#### 3.3 NewsAgent (新闻代理)
- **位置**: `/python/valuecell/agents/news_agent/`
- **功能**: 支持个性化定时新闻推送，实时跟踪关键信息
- **启动命令**: `uv run -m valuecell.agents.news_agent`
- **端口**: 自动分配

#### 3.4 StrategyAgent (策略代理)
- **位置**: `/python/valuecell/agents/strategy_agent/`
- **功能**: 提供交易策略分析和执行能力
- **启动命令**: `uv run -m valuecell.agents.strategy_agent`
- **端口**: 自动分配

### 4. Docker 配置

**位置**: `/docker/DockerFile`

**作用**:
- 提供后端服务的容器化部署方案
- 基于 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` 镜像
- 使用 uv 管理 Python 依赖

**构建和运行**:
```bash
# 构建镜像
docker build -t valuecell-backend -f docker/DockerFile python/

# 运行容器
docker run -p 8000:8000 valuecell-backend
```

## 运行方式

### 方式一：一键启动脚本（推荐）

**macOS/Linux**:
```bash
cd /Users/quyip/PycharmProjects/finance/valuecell
bash start.sh
```

**Windows (PowerShell)**:
```powershell
cd C:\path\to\valuecell
.\start.ps1
```

脚本会自动：
1. 检查并安装 `bun` 和 `uv`（如果缺失）
2. 安装前端依赖 (`bun install`)
3. 安装后端依赖 (`uv sync`)
4. 初始化数据库
5. 启动前端开发服务器（端口 1420）
6. 启动后端服务和所有代理（端口 8000 + 代理端口）

### 方式二：手动分步启动

#### 步骤 1: 配置环境变量

在项目根目录创建 `.env` 文件：
```bash
# LLM 提供商 API 密钥（至少配置一个）
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
# 或
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxx
# 或
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxx

# 可选：设置主提供商
PRIMARY_PROVIDER=openrouter

# 后端配置
API_HOST=0.0.0.0
API_PORT=8000

# 前端配置（如果需要）
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

#### 步骤 2: 安装依赖

**后端依赖**:
```bash
cd python
bash scripts/prepare_envs.sh
uv run valuecell/server/db/init_db.py
```

**前端依赖**:
```bash
cd frontend
bun install
```

#### 步骤 3: 启动服务

**终端 1 - 启动前端**:
```bash
cd frontend
bun run dev
```
前端将在 `http://localhost:1420` 启动

**终端 2 - 启动后端和代理**:
```bash
cd python
uv run --with questionary scripts/launch.py
```

这会启动：
- 后端 API 服务（端口 8000）
- ResearchAgent
- AutoTradingAgent
- NewsAgent
- StrategyAgent

### 方式三：使用 Docker（仅后端）

**构建镜像**:
```bash
docker build -t valuecell-backend -f docker/DockerFile python/
```

**运行容器**:
```bash
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/valuecell.db:/app/valuecell.db \
  valuecell-backend
```

**注意**: Docker 方式只包含后端服务，前端仍需单独启动。

## 组件间通信机制

### 1. 前端 ↔ 后端

**通信方式**:
- **REST API**: 用于常规 CRUD 操作（获取代理列表、对话历史等）
- **SSE (Server-Sent Events)**: 用于实时流式响应（代理对话）

**API 基础 URL**: `http://localhost:8000/api/v1`

**主要接口**:
```typescript
// REST API 示例
GET  /api/v1/agents              // 获取代理列表
GET  /api/v1/conversations      // 获取对话列表
POST /api/v1/conversations      // 创建新对话

// SSE 流式接口
POST /api/v1/agents/stream      // 发送查询并接收流式响应
```

**前端实现位置**:
- API 客户端: `frontend/src/lib/api-client.ts`
- SSE 客户端: `frontend/src/lib/sse-client.ts`
- 使用 Hook: `frontend/src/hooks/use-sse.ts`

### 2. 后端 ↔ 代理

**通信方式**:
- **A2A Protocol (Agent-to-Agent)**: 基于 HTTP 的标准化代理通信协议
- 后端通过 `AgentClient` 与代理通信
- 代理通过 HTTP 服务器暴露 A2A 接口

**为什么使用 A2A Protocol 而不是直接通信？**

采用 A2A Protocol 而非直接函数调用或自定义协议，主要基于以下设计考虑：

#### 1. **位置透明性 (Location Transparency)**
- **本地/远程无差别**: 代理可以运行在同一进程、不同进程、不同机器，甚至不同网络
- **无需修改代码**: 后端代码不需要知道代理的具体位置，只需知道 URL
- **灵活部署**: 可以将代理部署到云服务器、边缘设备或本地，后端代码无需改动

```python
# 后端代码只需要知道 URL，不需要知道代理在哪里
agent_url = "http://localhost:5001"  # 本地
# 或
agent_url = "http://192.168.1.100:8000"  # 远程
# 或
agent_url = "https://agent.example.com"  # 云端
```

#### 2. **标准化和互操作性**
- **标准协议**: A2A 是一个标准化的 Agent-to-Agent 通信协议，由 `a2a-sdk` 实现
- **跨平台兼容**: 任何遵循 A2A 协议的代理都可以与后端通信
- **社区生态**: 可以集成社区开发的代理，无需修改后端代码
- **未来扩展**: 支持新的传输层（如 WebSocket、gRPC）而无需修改业务逻辑

#### 3. **Agent Card 机制 (能力发现)**
- **自动发现能力**: 通过 Agent Card，后端可以自动发现代理的能力、输入/输出模式
- **动态选择**: Planner 可以根据 Agent Card 自动选择最合适的代理
- **版本管理**: Agent Card 包含版本信息，支持代理升级和兼容性检查

```python
# 后端自动获取代理能力
agent_card = await card_resolver.get_agent_card()
# 包含: name, description, capabilities, input/output modes 等
```

#### 4. **解耦和可扩展性**
- **完全解耦**: 后端和代理完全解耦，可以独立开发、测试、部署
- **独立扩展**: 每个代理可以独立扩展（水平扩展、垂直扩展）
- **故障隔离**: 一个代理的故障不会影响其他代理或后端
- **技术栈自由**: 代理可以用不同的语言/框架实现，只要遵循 A2A 协议

#### 5. **流式响应支持**
- **标准化流式事件**: A2A 定义了标准化的流式事件格式 (`TaskStatusUpdateEvent`)
- **实时进度**: 支持实时返回任务进度、中间结果、错误信息
- **事件驱动**: 基于事件驱动的架构，支持复杂的异步交互

#### 6. **独立部署和扩展**
- **独立进程**: 每个代理运行在独立进程中，可以独立重启、升级
- **资源隔离**: 每个代理有独立的资源限制，不会相互影响
- **水平扩展**: 可以运行多个相同代理的实例，实现负载均衡

#### 7. **错误处理和重试**
- **协议层错误处理**: A2A 协议定义了标准化的错误类型和处理机制
- **网络容错**: HTTP 层面的重试、超时、连接池等机制
- **优雅降级**: 代理不可用时，后端可以优雅处理，不影响整体系统

#### 8. **推送通知支持**
- **双向通信**: 支持代理主动推送通知到后端（如定时任务完成、异常告警）
- **事件订阅**: 后端可以订阅代理的特定事件
- **异步通知**: 不阻塞主流程，提高系统响应性

**对比直接通信的劣势**:

如果使用直接函数调用或自定义协议：

```python
# ❌ 直接调用方式的问题
class ResearchAgent:
    async def process(self, query: str):
        # 只能在同一进程调用
        pass

# 问题：
# 1. 必须运行在同一进程，无法分布式部署
# 2. 需要导入具体类，紧耦合
# 3. 无法动态发现能力
# 4. 难以实现流式响应
# 5. 错误处理不统一
# 6. 无法独立扩展和部署
```

**通信流程**:
```
后端 (AgentClient)
  ↓ HTTP Request (A2A Protocol)
代理 (A2A Server)
  ↓ 处理查询
代理 (LLM/工具调用)
  ↓ 生成响应
代理 (A2A Response - TaskStatusUpdateEvent)
  ↓ HTTP Response (Streaming)
后端 (接收流式事件)
  ↓ 转换为 SSE
前端 (实时显示)
```

**后端实现位置**:
- 代理客户端: `python/valuecell/core/agent/client.py`
- 连接管理: `python/valuecell/core/agent/connect.py`
- 流式服务: `python/valuecell/server/services/agent_stream_service.py`

**代理配置**:
- 代理卡片配置: `python/configs/agent_cards/*.json`
- 每个代理卡片包含：
  - 代理名称和描述
  - 代理服务 URL
  - 能力定义 (capabilities)
  - 输入/输出模式 (input/output modes)
  - 版本信息

### 3. 代理内部架构

每个代理遵循 A2A 协议规范：

```
代理服务启动
  ↓
注册 AgentCard (描述能力)
  ↓
监听 HTTP 请求 (A2A 端点)
  ↓
接收用户查询
  ↓
调用 LLM/工具处理
  ↓
返回流式响应 (TaskStatusUpdateEvent)
```

**代理实现位置**:
- 代理装饰器: `python/valuecell/core/agent/decorator.py`
- 代理响应: `python/valuecell/core/agent/responses.py`

## 数据流示例

### 用户发送消息的完整流程

```
1. 用户在 UI 输入消息
   ↓
2. 前端通过 SSE 发送到 /api/v1/agents/stream
   ↓
3. 后端 AgentStreamService 接收请求
   ↓
4. 后端通过 AgentClient 发送到对应代理
   ↓
5. 代理处理查询（调用 LLM、工具等）
   ↓
6. 代理返回流式事件 (TaskStatusUpdateEvent)
   ↓
7. 后端 ResponseRouter 转换为 BaseResponse
   ↓
8. 后端 ResponseBuffer 聚合和持久化
   ↓
9. 后端通过 SSE 流式发送到前端
   ↓
10. 前端实时渲染响应
```

### 对话持久化

- **存储位置**: SQLite 数据库 (`valuecell.db`)
- **存储内容**:
  - 对话记录
  - 消息历史
  - 任务状态
  - 用户配置
- **实现位置**: `python/valuecell/server/db/`

## 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端开发服务器 | 1420 | Vite dev server |
| 前端 HMR | 1421 | Hot Module Replacement |
| 后端 API | 8000 | FastAPI server |
| ResearchAgent | 自动分配 | 从 5000 开始查找可用端口 |
| AutoTradingAgent | 自动分配 | 从 5000 开始查找可用端口 |
| NewsAgent | 自动分配 | 从 5000 开始查找可用端口 |
| StrategyAgent | 自动分配 | 从 5000 开始查找可用端口 |
| 通知监听器 | 自动分配 | 每个代理可选的推送通知端点 |

## 日志管理

**日志位置**: `logs/{timestamp}/`

**日志文件**:
- `backend.log` - 后端服务日志
- `ResearchAgent.log` - 研究代理日志
- `AutoTradingAgent.log` - 自动交易代理日志
- `NewsAgent.log` - 新闻代理日志
- `StrategyAgent.log` - 策略代理日志

**查看日志**:
```bash
# 查看最新日志目录
ls -lt logs/ | head -2

# 查看后端日志
tail -f logs/$(ls -t logs/ | head -1)/backend.log

# 查看代理日志
tail -f logs/$(ls -t logs/ | head -1)/ResearchAgent.log
```

## 常见问题

### 1. 端口被占用

**问题**: 端口 1420 或 8000 已被占用

**解决**:
```bash
# 查找占用端口的进程
lsof -ti:1420
lsof -ti:8000

# 杀死进程
kill -9 $(lsof -ti:1420)
kill -9 $(lsof -ti:8000)
```

### 2. 代理连接失败

**问题**: 后端无法连接到代理服务

**检查**:
1. 确认代理服务已启动
2. 检查代理 URL 配置 (`python/configs/agent_cards/*.json`)
3. 查看代理日志确认服务正常运行

### 3. 数据库错误

**问题**: 数据库兼容性错误

**解决**:
```bash
# 删除旧数据库文件
rm -rf lancedb/
rm -f valuecell.db
rm -rf .knowledgebase/

# 重新初始化
cd python
uv run valuecell/server/db/init_db.py
```

### 4. API 密钥未配置

**问题**: LLM 调用失败

**解决**:
1. 检查 `.env` 文件是否存在
2. 确认至少配置了一个 LLM 提供商的 API 密钥
3. 验证 API 密钥有效性

## 开发模式 vs 生产模式

### 开发模式（当前默认）

- 前端: Vite dev server，支持热重载
- 后端: Uvicorn 开发服务器，自动重载
- 日志: 详细的控制台输出
- 数据库: SQLite 本地文件

### 生产模式

**前端构建**:
```bash
cd frontend
bun run build
```

**后端生产运行**:
```bash
cd python
uv run uvicorn valuecell.server.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

**使用 Docker**:
```bash
docker build -t valuecell-backend -f docker/DockerFile python/
docker run -d -p 8000:8000 valuecell-backend
```

## 访问应用

启动成功后：

- **Web UI**: http://localhost:1420
- **API 文档**: http://localhost:8000/docs (如果 `API_DEBUG=true`)
- **健康检查**: http://localhost:8000/

## 停止服务

**使用启动脚本启动的**:
- 按 `Ctrl + C` 停止，脚本会自动清理所有进程

**手动启动的**:
- 在每个终端窗口按 `Ctrl + C` 停止对应服务
- 或使用 `pkill` 命令：
```bash
pkill -f "bun run dev"      # 停止前端
pkill -f "uv run.*launch"   # 停止后端和代理
```


