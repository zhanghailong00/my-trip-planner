# 智能旅行规划助手 (Smart Trip Planner) 🌍✈️

基于 **LangGraph** 多智能体框架与 **Vue 3** 构建的下一代智能旅行规划系统。只需输入目的地和偏好，AI 助手即可为您生成包含景点、天气、酒店建议及高德地图交互的完整行程。

---

## 🌟 核心特性

- **多智能体协同**：利用 LangGraph 构建有状态的工作流，实现景点搜索、实时天气获取、周边酒店匹配的并行处理。
- **高德地图深度集成**：
    - **后端**：通过高德 Web API 获取精准的 POI (兴趣点) 数据。
    - **前端**：使用高德 JS API 2.0 实时渲染景点标记，支持点击交互。
- **现代化 UI/UX**：基于 Vue 3 + Ant Design Vue 打造，提供清晰的行程时间线与地图联动体验。
- **安全配置**：统一的环境变量管理，支持 OpenAI、DeepSeek 等多种主流大模型。

---

## 🏗️ 技术架构

### 后端 (Backend)
- **框架**: FastAPI
- **AI 编排**: LangGraph + LangChain
- **模型支持**: OpenAI, DeepSeek (通过 OpenAI 兼容接口)
- **数据源**: 高德地图 Web 服务 API

### 前端 (Frontend)
- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite + TypeScript
- **UI 组件库**: Ant Design Vue
- **地图展示**: 高德地图 JS API 2.0

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/zhanghailong00/my-trip-planner.git
cd my-trip-planner
```

### 2. 环境配置
在项目根目录创建 `.env` 文件，并参考 `.env.example` 填写您的 API Key：

```env
# 高德地图配置
AMAP_API_KEY=您的Web服务Key
AMAP_SECURITY_CODE=您的安全密钥
VITE_AMAP_JS_KEY=您的浏览器端Key

# LLM 配置
LLM_PROVIDER=openai
OPENAI_API_KEY=您的API_Key
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
```

### 3. 启动后端
```bash
cd backend
pip install -r requirements.txt
python run.py
```
后端将运行在：`http://localhost:8001`

### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```
前端将运行在：`http://localhost:5173`

---

## 📁 项目结构

```text
my-trip-planner/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── agents/         # LangGraph 多智能体逻辑
│   │   ├── api/            # 接口路由
│   │   ├── services/       # 高德地图与 LLM 封装
│   │   └── models/         # Pydantic 数据模型
│   └── run.py              # 服务入口
├── frontend/               # Vue 3 前端
│   ├── src/
│   │   ├── views/          # 页面组件 (Home/Result)
│   │   ├── services/       # API 请求封装
│   │   └── types/          # TS 类型定义
│   └── vite.config.ts      # 代理配置
└── .env                    # 统一环境变量 (不上传)
```

---

## 🛠️ 后续计划

- [ ] 增加用户账户系统，支持保存与分享行程。
- [ ] 引入更多维度的搜索（如餐厅评价、交通流量）。
- [ ] 优化地图路径规划的动态展示。
- [ ] 支持多语言行程生成。

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 协议开源。
