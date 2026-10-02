# God Eye System（天眼系统）

> ⚠️ **重要许可声明：本项目为【源码可见 Source‑Available】，不属于 OSI 定义的开源项目**
>
> - ✅ 允许：个人非商业场景，**不修改源代码前提下本地部署、学习研究**
> - ❌ 禁止：未经版权方书面授权，修改代码、制作衍生版本、Fork、公开发布、二次分发
> - ❌ 禁止：任何商业用途，包括企业内部部署、SaaS服务、打包售卖、集成到商业产品
> - 💼 商业使用、修改、分发，需要购买商业授权，联系邮箱：**liudashang@sina.com**
>
> 完整法律许可条款，请查看仓库根目录 [`LICENSE`](./LICENSE) 文件。

> IT系统拓扑结构、动态监控告警、网络Ping监控、延迟丢包告警可视化平台，基于Flask + MySQL/MariaDB + ClickHouse + Grafana构建

## 📋 项目简介
God Eye System（天眼系统）是面向运维场景的 IT 网络可视化与监控告警大屏工具。支持 IT 系统网络拓扑动态展示，可完整呈现服务器、存储、网络设备等各类硬件资产的网络架构；同时集成多节点 Ping 链路探测能力，完成延迟、丢包数据采集与异常告警，并对接 Grafana 实现监控数据可视化。帮助运维工程师高效完成日常巡检，快速定位、排查网络故障。
- 后端框架：Flask
- 业务数据库：MySQL8.0 / MariaDB
- 时序存储：ClickHouse
- 可视化面板：Grafana 13.0
- 客户端：Windows Ping探测客户端（看门狗自动保活）

## ⚠️ 环境前置要求
> **仅支持 Linux 操作系统，推荐 Ubuntu Server**
| 软件 | 版本要求 |
|---|---|
| Python | >=3.10 |
| Grafana | 13.0 |
| ClickHouse | 最新稳定版 |
| MySQL / MariaDB | MySQL8.0 或 MariaDB |

## 🚀 服务端部署步骤
### 1. 拉取代码仓库
```bash
git clone [https://github.com/liudashang/god_eye_system.git](https://github.com/liudashang/god_eye_system.git)
cd god_eye_system
```

### 2. 创建Python虚拟环境

```
# 创建虚拟环境
python3 -m venv .venv
# 激活虚拟环境
source .venv/bin/activate
```

### 3. MySQL数据库初始化

登录MySQL客户端，执行下面SQL，创建业务库与账号：

```
-- 创建访问用户，允许任意地址访问
CREATE USER 'god_eye'@'%' IDENTIFIED BY 'godEye1234.';

-- 创建业务数据库，使用utf8mb4字符集
CREATE DATABASE god_eye_system_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 授权
GRANT ALL PRIVILEGES ON god_eye_system_db.* TO 'god_eye'@'%';
FLUSH PRIVILEGES;
```

### 4. 配置环境变量

复制示例环境配置文件，生成`.env`

```
cp .env.example .env
```

编辑 `.env` 文件，修改数据库配置：

```
DATABASE_USER=god_eye
DATABASE_PASSWORD=godEye1234.
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=god_eye_system_db

# 填写项目内 downloads 目录的绝对路径
DOWNLOAD_FILE_PATH=/home/super/py_project/god_eye_system/downloads

# ClickHouse配置，后续创建库之后修改
CLICKHOUSE_HOST=localhost
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_PORT=9000
CLICKHOUSE_DATABASE=test_db
```

### 5. 安装Python依赖包

> 
> 确认已经激活虚拟环境 `.venv`

```
pip3 install -r requirements.txt
```

### 6. 项目基础校验

运行入口脚本，确认无报错输出：

```
python3 autoapp.py
```

### 7. Flask数据库迁移初始化

```
flask db init
flask db migrate
flask db upgrade
```

### 8. ClickHouse 时序库初始化

1. 在ClickHouse服务中手动创建数据库，示例库名 `test_db`

```
CREATE DATABASE test_db;
```

2. 执行项目脚本文件 `god_eye_system/ping_web_service/clickhouse_create_table.sql` 内全部SQL，完成数据表创建
3. 确认 `.env` 中 ClickHouse 相关参数与实际环境匹配

### 9. 启动主Web服务

```
flask run
```

### 10. 初始化管理员账号

访问注册接口完成管理员`admin`账号注册，将`my_ip`替换为你的服务器IP地址

```
http://<my_ip>:5000/test_register/
```

## 📊 Grafana看板配置

> 
> Grafana版本要求：13.0

1. 打开Grafana Web界面，点击左侧`Dashboards`
2. 点击右上角 `New` → **Import dashboard**
3. 导入项目内看板文件：`ping_monitor/dashboard-grafana-ping.json`
4. 参考文档 `pytools/once_job/grafana配置.txt`，开启Grafana JWT认证模式

## 🧩 附属后台服务启动

> 
> 全部服务建议在虚拟环境内运行，每个服务建议独立终端会话执行

1. **Ping客户端Web服务（接收Windows客户端上报数据）**

```
cd ping_web_service
python3 app.py
```

2. **Ping监控守护服务（检测客户端运行状态异常告警）**

```
cd ping_monitor
python3 ping_monitor.py
```

3. **告警检测服务（延迟、丢包告警消息推送展示）**

```
cd pytools/apsecheduler
python3 alert_check.py
```

## 🖥️ Windows Ping 探测客户端

> 
> 客户端仅可在Windows系统运行，自带看门狗，程序异常会自动重启

1. 获取客户端压缩包：`ping_client/god_ping_client.rar`
2. Windows下解压压缩包
3. 双击运行 `启动程序.bat`

## 📁 项目目录简要说明

```
god_eye_system
├── ping_web_service        # ping客户端上报web服务，clickhouse建表SQL
├── ping_monitor            # ping状态监控、grafana看板json
├── pytools
│   ├── once_job            # grafana jwt配置说明文档
│   └── apsecheduler        # 告警检测定时任务
├── ping_client             # Windows ping探测客户端程序包
├── downloads               # 文件下载存储目录（.env配置绝对路径）
├── autoapp.py              # 项目主入口校验脚本
├── requirements.txt        # python依赖清单
├── .env.example            # 环境变量模板
```

## ⚠️ 注意事项

1. 所有后端Python服务需要在同一个虚拟环境 `.venv` 中运行
2. 防火墙需要开放：Flask(5000)、ClickHouse(9000)、Grafana(3000)，Ping Web服务对应端口
3. Windows ping客户端网络需要能够访问服务端对应接口地址
4. 生产环境不建议直接使用 `flask run`，推荐使用 gunicorn / uwsgi 部署web服务
5. 默认数据库密码仅用于测试，生产部署务必修改MySQL、ClickHouse账号密码

> 
> 开发环境部署文档，生产环境需要做进程托管(supervisor/systemd)、Nginx反向代理、账号密码加固。

## License

本项目源码可见，**非开源软件**。
完整许可条款参见仓库根目录 [`LICENSE`](./LICENSE) 文件。

- 非商业用户：允许不修改源码前提下本地部署学习；禁止修改、衍生、Fork、分发。
- 商业使用、修改、二次分发，必须取得版权持有人书面商业授权。
商业授权联系：天之道风‑[liudashang@sina.com](mailto:liudashang@sina.com)
