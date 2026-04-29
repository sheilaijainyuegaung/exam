# Exam Recognition System

试卷识别系统，包含前端上传界面和后端识别服务。

适用场景：
- 上传试卷文档并创建识别任务
- 查看任务状态、提取结果和结构详情
- 按题型结构展示分值树
- 管理规则配置并持续修正规则

## 目录结构

```text
shijuanshibie/
├─ backend/                  后端服务（FastAPI）
│  ├─ app/                   业务代码
│  ├─ scripts/               后端启动脚本
│  ├─ sql/                   数据库初始化脚本
│  └─ storage/               运行时上传文件和分页产物目录
├─ 前端项目源码（fre）/       前端项目（Vue 2）
├─ start_all.bat             Windows 开发启动脚本
├─ start_exam_system_ubuntu.sh
│                            Ubuntu 一键安装并启动脚本
├─ stop_exam_system_ubuntu.sh
│                            Ubuntu 停止脚本
└─ deploy_db_env_ubuntu.sh   Ubuntu 数据库/环境辅助脚本
```

## 技术栈

- 前端：Vue 2、Vue Router
- 后端：FastAPI、Uvicorn
- 数据库：MySQL
- 文档处理：LibreOffice

## 默认端口

- 前端：`8080`
- 后端：`8001`
- Swagger：`http://127.0.0.1:8001/docs`

## 运行前准备

### 1. 数据库

先创建 MySQL 数据库，并执行：

```sql
mysql -uroot -proot < backend/sql/schema.sql
```

默认数据库连接串：

```text
mysql+pymysql://root:root@127.0.0.1:3306/exam_recognition?charset=utf8mb4
```

如果你有自己的数据库配置，可以在运行前设置环境变量 `DATABASE_URL`。

### 2. 后端依赖

```bash
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 前端依赖

```bash
cd 前端项目源码（fre）
npm install
```

### 4. LibreOffice

后端识别文档时依赖 `soffice`，服务器上需要可执行：

```bash
soffice --version
```

如果没有安装，在 Ubuntu 上可执行：

```bash
sudo apt-get update
sudo apt-get install -y libreoffice
```

## 本地开发

### Windows

项目根目录执行：

```powershell
start_all.bat
```

只检查路径和环境，不启动服务：

```powershell
start_all.bat --check
```

### 单独启动后端

```powershell
cd backend
.\scripts\run_windows.ps1
```

### 单独启动前端

```powershell
cd 前端项目源码（fre）
npm run serve
```

## Ubuntu 部署

项目根目录执行：

```bash
chmod +x start_exam_system_ubuntu.sh
./start_exam_system_ubuntu.sh
```

这个脚本会自动完成：
- 创建后端虚拟环境
- 安装后端依赖
- 安装前端依赖
- 构建前端 `dist`
- 启动后端服务
- 用静态服务托管前端构建产物

停止服务：

```bash
chmod +x stop_exam_system_ubuntu.sh
./stop_exam_system_ubuntu.sh
```

## 关键路径

- 后端主入口：[backend/app/main.py](/E:/xiangmudaima/shijuanshibie/backend/app/main.py)
- 后端说明：[backend/README.md](/E:/xiangmudaima/shijuanshibie/backend/README.md)
- 前端说明：[前端项目源码（fre）/README.md](/E:/xiangmudaima/shijuanshibie/前端项目源码（fre）/README.md)
- Windows 启动脚本：[start_all.bat](/E:/xiangmudaima/shijuanshibie/start_all.bat)
- Ubuntu 启动脚本：[start_exam_system_ubuntu.sh](/E:/xiangmudaima/shijuanshibie/start_exam_system_ubuntu.sh)
- Ubuntu 停止脚本：[stop_exam_system_ubuntu.sh](/E:/xiangmudaima/shijuanshibie/stop_exam_system_ubuntu.sh)

## 常用接口

- `POST /api/v1/recognitions/upload`
- `GET /api/v1/recognitions/tasks/{taskId}`
- `GET /api/v1/recognitions/tasks/{taskId}/result`
- `GET /api/v1/recognitions/tasks/{taskId}/details`
- `POST /api/v1/rule-profiles`
- `GET /api/v1/rule-profiles`
- `PUT /api/v1/rule-profiles/{id}`

## 部署说明

- 当前仓库已经清理掉大部分测试、临时校验和本地调试产物，适合直接作为部署基础。
- `backend/storage/` 是运行期目录，部署后会自动产生上传文件和分页缓存。
- 前端目录已经统一为 `前端项目源码（fre）`，启动脚本也已同步。
- 如果服务器是全新环境，第一次部署时需要重新安装 Python 依赖和 Node 依赖，这是正常的。

## 建议

- 生产环境建议把 `DATABASE_URL`、`LIBREOFFICE_CMD` 放到后端 `.env` 中统一管理。
- 建议把 `backend/storage/` 放在可持久化磁盘上。
- 如果后续继续做规则修复，优先在后端规则层维护，不要直接改部署脚本。
