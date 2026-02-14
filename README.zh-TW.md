
[English](README.md) | [繁體中文](README.zh-TW.md)

![Stars](https://img.shields.io/github/stars/SeanChangX/THSR-Sniper)
![Release](https://img.shields.io/github/v/release/SeanChangX/THSR-Sniper)
![Downloads](https://img.shields.io/github/downloads/SeanChangX/THSR-Sniper/total)
![Docker Pulls](https://img.shields.io/docker/pulls/seanchangx/thsr-sniper?logo=docker&logoColor=white&label=seanchangx%2Fthsr-sniper)
![License](https://img.shields.io/github/license/SeanChangX/THSR-Sniper)

# THSR-Sniper

```

        ________  _______ ____              _____       _                
       /_  __/ / / / ___// __ \            / ___/____  (_)___  ___  _____
        / / / /_/ /\__ \/ /_/ /  ______    \__ \/ __ \/ / __ \/ _ \/ ___/
       / / / __  /___/ / _, _/  /_____/   ___/ / / / / / /_/ /  __/ /    
      /_/ /_/ /_//____/_/ |_|            /____/_/ /_/_/ .___/\___/_/     
                                                     /_/                 

# Taiwan High Speed Rail (THSR) 自動化訂票系統
# 具備智慧自動化、OCR 驗證碼辨識、API 伺服器、任務排程，
# 並支援多服務架構與 Docker 部署。
```

## 截圖

<div align="center">
  <img src="docs/screenshots/login-page.png" alt="Login Page" width="45%">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard Overview" width="45%">
  <br>
  <img src="docs/screenshots/booking-form.png" alt="Booking Form" width="45%">
  <img src="docs/screenshots/task-management.png" alt="Task Management" width="45%">
</div>

## 快速開始

### 使用 Docker（建議）

```bash
# 下載專案
git clone https://github.com/SeanChangX/THSR-Sniper.git
cd THSR-Sniper
```

### 初始設定

第一次啟動服務前，需先設定環境檔：

#### 1. 產生安全金鑰

使用腳本產生 JWT 與加密金鑰：

```bash
python3 generate_keys.py
```

此步驟會建立 `.env` 檔案，包含：
- `SECRET_KEY` - JWT 驗證用金鑰（隨機產生）
- `ENCRYPTION_KEY` - 資料加密金鑰（隨機產生）

#### 2. 加入 MySQL 設定

將 MySQL 設定附加到 `.env`：

```bash
# 將 env.example 的 MySQL 設定附加到 .env
cat env.example | grep -A 4 "MySQL Database" >> .env
```

或直接手動編輯 `.env` 加入以下內容：
```env
# MySQL Database Configuration
MYSQL_ROOT_PASSWORD=thsr_sniper_root
MYSQL_DATABASE=thsr_sniper
MYSQL_USER=user
MYSQL_PASSWORD=password
```

若未設定將使用預設值。正式環境建議更改密碼。

#### 3. 前端設定（選用）

前端預設 API 端點可搭配 Docker 使用：

```bash
# 複製前端環境範本（選用，如需自訂）
cp frontend/env.example frontend/.env
```

#### 4. 建置服務（選用）

```bash
# 建置服務
docker compose build
```

### 環境啟動

#### 正式環境
適用於最佳化建置：
```bash
# 啟動正式環境
docker compose up -d

# 服務位址：
# - Frontend:   http://localhost:3000 [ Production ]
```

#### 開發環境

前端熱更新開發：
```bash
# 以 Vite Dev Server 啟動開發環境
docker compose -f docker-compose.dev.yml up -d

# 服務位址：
# - Frontend:         http://localhost:5173 [ Vite Dev Server ]
# - API server:       http://localhost:8000
# - Auth service:     http://localhost:8001
# - MySQL database:   http://localhost:3306
# - phpMyAdmin:       http://localhost:8080
```

### 三種操作模式

#### 1. 立即訂票（CLI 模式）
直接執行訂票：
```bash
# 互動模式（引導式）
docker compose run --rm thsr-sniper python main.py

# 指令列模式（完整參數）
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --date 2026/01/01 --time 20 \
  --adult 1 --seat 0 --class 0 --train 1 --id A123456789 --member n
```

#### 2. 排程訂票（API + Scheduler）
定期自動嘗試訂票：
```bash
# 啟動完整系統（API + Scheduler + Watchdog）
docker compose up -d

# 建立排程任務
docker compose exec thsr-sniper python main.py --schedule \
  --from 2 --to 11 --adult 1 --date +1 --id A123456789 --member n \
  --interval 5 --max-attempts 50

# 管理任務
docker compose exec thsr-sniper python main.py --list-tasks
docker compose exec thsr-sniper python main.py --task-status TASK_ID
docker compose exec thsr-sniper python main.py --cancel-task TASK_ID
```

#### 3. API 伺服器模式
提供 RESTful API 供整合與前端使用：
```bash
# 僅啟動 API 伺服器
docker compose up -d thsr-sniper-api

# API 位址：http://localhost:8000
# 文件位址：http://localhost:8000/docs
```

## 指令列選項

### 個人資訊
- `--id, -i` - 身分證字號（訂票必填）
- `--member, -m` - 是否使用會員（y/n、true/false、1/0）

### 行程資訊
- `--from, -f` - 出發站 ID（使用 `--stations` 查看）
- `--to, -t` - 抵達站 ID（使用 `--stations` 查看）
- `--date, -d` - 出發日期（YYYY/MM/DD、YYYY-MM-DD 或相對日期：+1、+2、tomorrow）
- `--time, -T` - 出發時段 ID（使用 `--times` 查看）
- `--train, -r` - 車次索引（1, 2, 3...）

### 票種設定
- `--adult, -a` - 全票張數（0-10）
- `--student, -s` - 學生票張數（0-10）
- `--seat, -p` - 座位偏好：0=不限、1=靠窗、2=靠走道
- `--class, -c` - 車廂等級：0=標準、1=商務

### 排程選項（API 模式）
- `--schedule` - 建立排程訂票（需啟動 API）
- `--interval` - 訂票間隔（分鐘，預設 5）
- `--max-attempts` - 最多嘗試次數（未指定表示不限）
- `--list-tasks` - 列出所有排程任務
- `--task-status TASK_ID` - 顯示指定任務狀態
- `--cancel-task TASK_ID` - 取消指定任務

### API 伺服器選項
- `--start-api` - 啟動 API 伺服器
- `--api-host` - API 伺服器位址（預設 0.0.0.0）
- `--api-port` - API 伺服器埠號（預設 8000）

### 資訊與工具
- `--stations` - 列出所有車站與 ID
- `--times` - 列出所有時段與 ID
- `--no-ocr` - 關閉 OCR，自行輸入驗證碼

## 日期格式支援

系統支援多種輸入格式：

### 絕對日期
- `2026/01/15` (YYYY/MM/DD)
- `2026-01-15` (YYYY-MM-DD)
- `01/15/2026` (MM/DD/YYYY)
- `15/01/2026` (DD/MM/YYYY)

### 相對日期
- `+1` - 明天
- `+2` - 後天
- `+7` - 下週
- `tomorrow` 或 `tmr` - 明天
- `today` 或 `now` - 今天

## 車站對照

| ID | 車站 | ID | 車站 |
|----|------|----|------|
| 1  | 南港 | 7  | 台中 |
| 2  | 台北 | 8  | 彰化 |
| 3  | 板橋 | 9  | 雲林 |
| 4  | 桃園 | 10 | 嘉義 |
| 5  | 新竹 | 11 | 台南 |
| 6  | 苗栗 | 12 | 左營 |

## 時段

系統提供全天 38 個時段，從 00:01 到 23:30。使用 `--times` 查看完整清單。

## Docker 服務

本系統由多個 Docker 服務組成：

### 核心服務

#### `thsr-sniper`（主 CLI）
互動式 CLI，支援立即訂票與任務管理：
```bash
docker compose run --rm thsr-sniper python main.py [options]
```

#### `thsr-sniper-api`（RESTful API 伺服器）
提供 OpenAPI 文件的 Web API：
```bash
docker compose up -d thsr-sniper-api
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

#### `thsr-sniper-scheduler`（背景 Watchdog）
監控並執行排程任務：
```bash
docker compose up -d thsr-sniper-scheduler
# 自動處理排程訂票
```

## API 端點

### API 文件
- **互動式 API 文件**: http://localhost:8000/docs
- **Auth 服務文件**: http://localhost:8001/docs

REST API 提供完整訂票功能：

### 資訊類端點
- `GET /` - API 資訊與狀態
- `GET /stations` - 列出所有車站
- `GET /times` - 列出所有時段
- `GET /scheduler/status` - 排程狀態與統計

### 訂票端點
- `POST /book` - 立即訂票（單次嘗試）
- `POST /schedule` - 建立排程訂票

### 任務管理端點
- `GET /tasks` - 列出所有排程任務
- `GET /tasks/{task_id}` - 取得任務狀態
- `DELETE /tasks/{task_id}` - 取消任務
- `DELETE /tasks/{task_id}/remove` - 完整移除任務

### 結果與統計
- `GET /results` - 取得訂票結果（可篩選）
- `GET /results/stats` - 取得訂票統計
- `GET /results/{task_id}` - 取得任務詳細結果

## 使用範例

### 立即訂票範例

#### 基本訂票
```bash
# 從台北到台南，訂 1 張全票
docker compose run --rm thsr-sniper python main.py \
  --from 2 --to 11 --adult 1 --id A123456789 --member n
```

#### 全參數訂票
```bash
# 指定車次、座位偏好與商務車廂
docker compose run --rm thsr-sniper python main.py \
  --from 1 --to 12 --date 2026/01/01 --time 10 \
  --adult 1 --seat 1 --class 1 --train 1 \
  --id A123456789 --member n
```

#### 學生票與相對日期
```bash
# 訂明天的學生票
docker compose run --rm thsr-sniper python main.py \
  --from 5 --to 7 --student 2 --date +1 \
  --id A123456789 --member n
```

### 排程訂票範例

#### 啟動完整系統
```bash
# 啟動所有服務（API + Scheduler + Watchdog）
docker compose up -d
```

#### 建立排程任務
```bash
# 每 5 分鐘嘗試訂票一次
docker compose exec thsr-sniper python main.py --schedule \
  --from 2 --to 11 --adult 1 --date +3 \
  --id A123456789 --member n --interval 5
```

#### 進階排程設定
```bash
# 指定最大嘗試次數與偏好
docker compose exec thsr-sniper python main.py --schedule \
  --from 1 --to 12 --date 2026/01/01 --time 15 \
  --adult 2 --seat 1 --class 0 \
  --id A123456789 --member y \
  --interval 3 --max-attempts 100
```

### 任務管理範例

#### 列出所有任務
```bash
docker compose exec thsr-sniper python main.py --list-tasks
```

#### 查詢任務狀態
```bash
docker compose exec thsr-sniper python main.py --task-status abc12345-...
```

#### 取消任務
```bash
docker compose exec thsr-sniper python main.py --cancel-task abc12345-...
```

### API 使用範例

#### 使用 API 排程訂票
```bash
curl -X POST "http://localhost:8000/schedule" \
  -H "Content-Type: application/json" \
  -d '{
    "from_station": 2,
    "to_station": 11,
    "date": "2026/01/01",
    "personal_id": "A123456789",
    "use_membership": false,
    "adult_cnt": 1,
    "interval_minutes": 5
  }'
```

### 資訊與工具

#### 查看可用選項
```bash
# 列出所有車站
docker compose run --rm thsr-sniper python main.py --stations

# 列出所有時段
docker compose run --rm thsr-sniper python main.py --times
```

### 結果檢視
```bash
# 檢視訂票結果
./view_results.sh

# 顯示詳細結果
./view_results.sh --details

# 顯示特定使用者的結果
./view_results.sh --user 1 --details

# 顯示成功訂票
./view_results.sh --status success
```

## 專案結構
```
THSR-Sniper/                    # 台灣高鐵自動訂票系統
├── 🐳 Docker Services
│   ├── docker-compose.yml      # 正式環境多服務設定
│   ├── docker-compose.dev.yml  # 開發環境（熱更新）
│   └── Dockerfile              # 主應用容器定義
│
├── 🧠 核心應用（thsr_py/）
│   ├── __init__.py             # 套件初始化
│   ├── api.py                  # FastAPI 伺服器與驗證端點
│   ├── api_client.py           # API 客戶端（自動偵測 Docker）
│   ├── cli.py                  # CLI 介面與啟動畫面
│   ├── flows.py                # 訂票流程與自動化邏輯
│   ├── scheduler.py            # 智慧排程引擎
│   ├── schema.py               # 資料模型與常數（車站/時段）
│   └── watchdog.py             # 背景監控服務
│
├── 🛡️ 認證服務（auth_service/）
│   ├── auth_api.py             # JWT 驗證 API
│   ├── database.py             # MySQL 使用者管理
│   ├── security.py             # 密碼雜湊與 Token 驗證
│   ├── requirements.txt        # 認證服務套件
│   ├── Dockerfile              # 認證服務容器
│   └── data/                   # 資料庫初始化腳本
│
├── 🎨 前端介面（frontend/）
│   ├── src/                    # React + TypeScript 原始碼
│   │   ├── components/         # 依功能拆分的 UI 元件
│   │   │   ├── Dashboard.tsx   # 儀表板（統計與快捷動作）
│   │   │   ├── Layout.tsx      # 版面與導覽
│   │   │   ├── auth/           # 認證元件（登入、註冊）
│   │   │   ├── booking/        # 訂票表單與管理
│   │   │   ├── profile/        # 使用者資料管理
│   │   │   ├── tasks/          # 任務監控與管理
│   │   │   └── ui/             # 共用元件（Spinner、通知）
│   │   ├── services/           # API 整合層
│   │   │   └── api.ts          # API 客戶端（含驗證）
│   │   ├── store/              # 狀態管理（Zustand）
│   │   │   └── authStore.ts    # 認證狀態
│   │   ├── types/              # TypeScript 型別
│   │   │   └── index.ts        # 共用介面
│   │   ├── utils/              # 工具函式
│   │   │   ├── dateTime.ts     # 日期格式與時區處理
│   │   │   └── stations.ts     # 車站對照與路線格式化
│   │   ├── App.tsx             # 主程式與路由
│   │   ├── main.tsx            # 入口點
│   │   ├── index.css           # 全域樣式（ROG 風格主題）
│   │   └── vite-env.d.ts       # Vite 型別
│   ├── public/                 # 靜態資源
│   ├── package.json            # Node.js 套件
│   ├── vite.config.ts          # Vite 設定（含 proxy）
│   ├── tailwind.config.js      # Tailwind CSS 主題
│   ├── postcss.config.js       # PostCSS 設定
│   ├── tsconfig.json           # TypeScript 設定
│   ├── tsconfig.node.json      # Node.js TS 設定
│   ├── index.html              # HTML 入口
│   ├── nginx.conf              # Production nginx 設定
│   ├── Dockerfile              # Production build 容器
│   ├── Dockerfile.dev          # Development 容器
│   ├── .dockerignore           # Docker 忽略設定
│   └── env.example             # 環境變數範本
│
├── 🧠 ML 驗證碼辨識（thsr_ocr/）
│   ├── captcha_ocr.py          # CNN+LSTM+CTC 訓練
│   ├── download_captcha.py     # 驗證碼下載
│   ├── prediction_model.py     # 推論用模型
│   ├── test_model.py           # 準確度測試
│   ├── datasets/               # 訓練資料與前處理
│   └── *.keras                 # 已訓練模型（95%+ 準確率）
│
├── 📊 結果與分析
│   ├── view_results_direct.py  # 直接查詢資料庫
│   ├── view_results.sh         # Docker 包裝腳本
│   ├── main.py                 # 主入口與 CLI 路由
│   └── generate_keys.py        # 金鑰產生器
│
├── 📁 資源與文件
│   ├── assets/                 # 專案資產
│   │   └── thsr-sniper-logo.svg
│   ├── README.md               # 英文說明
│   ├── requirements.txt        # 主要 Python 相依套件
│   ├── LICENSE                 # MIT License
│   └── env.example             # 環境變數範本
```

## 技術細節

### 驗證碼 OCR 系統

- **深度學習架構**：針對 THSR 設計的 CNN+LSTM+CTC 模型
- **自動辨識**：最多 3 次嘗試，失敗改手動輸入
- **模型規格**：160x50 灰階輸入、THSR 專用字元集
- **訓練流程**：含資料管理與模型轉換工具
- **整合方式**：與訂票流程完整整合，含錯誤處理

### 排程引擎

- **持久化儲存**：JSON 任務序列化與原子寫入
- **狀態追蹤**：六種狀態（pending/running/success/failed/expired/cancelled）
- **重試邏輯**：可設定間隔與最大嘗試次數
- **並行處理**：執行緒安全並帶鎖
- **健康監測**：Watchdog 自動重啟能力

### API 架構

- **FastAPI**：現代化 Python Web 框架，含自動文件
- **RESTful**：標準 HTTP 方法與狀態碼
- **驗證**：Pydantic 參數驗證
- **錯誤處理**：結構化錯誤回應
- **CORS**：支援跨域存取

## 免責聲明

**本軟體僅供學術研究與教育用途。**

- 本專案為非官方實作，與台灣高鐵（THSR）無任何關聯
- 使用風險由使用者自行承擔
- 使用者需自行遵守相關法規
- 開發者不對任何使用造成的損害或法律問題負責
- 本工具旨在網頁自動化與 CLI 開發之教學與研究
