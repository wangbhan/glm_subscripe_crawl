# GLM Coding 自动抢购脚本

自动化抢购 [智谱AI GLM Coding](https://bigmodel.cn/glm-coding) 订阅服务的 Python 脚本。基于 Playwright 浏览器自动化，支持定时调度、自动重试和消息推送通知。

## 功能特性

- **浏览器自动化** — 使用 Playwright 持久化上下文，自动复用登录态，无需重复登录
- **提前预热** — 提前 10~20 分钟打开页面，避开高峰期网站卡顿
- **精确定时** — 自旋等待精确到 10ms，在目标时间点准时刷新并点击
- **多轮重试** — 支持配置多轮重试（每轮内多次尝试），提高抢购成功率
- **消息推送** — 通过 [ntfy](https://ntfy.sh) 推送抢购进度到手机/微信
- **截图记录** — 关键节点自动截图，方便排查问题
- **配置驱动** — 所有参数集中在 YAML 配置文件，修改无需改代码

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 创建配置文件

```bash
# 配置模板已提供，复制并填写实际值
copy config_example.yaml config.yaml
```

编辑 `config.yaml`，填写以下内容：

```yaml
# 页面元素选择器（需用浏览器 F12 确认）
selectors:
  subscribe_button: ""    # 购买/订阅按钮的 CSS 选择器
  payment_dialog: ""      # 支付弹窗的 CSS 选择器

# ntfy 推送通知
ntfy:
  enabled: true
  url: "https://ntfy.sh/你的topic"
```

### 3. 首次登录

```bash
python main.py --login
```

脚本会打开浏览器，手动完成智谱账号登录后按 Enter，登录态自动保存到 `browser_data/` 目录。

### 4. 启动抢购

```bash
# 方式一：定时调度（默认 9:40 提前预热，9:59 开始抢购）
python main.py

# 方式二：立即执行一次（用于测试）
python main.py --now
```

## 如何获取 CSS 选择器

`config.yaml` 中的 `selectors` 需要手动填写，获取方法：

1. 用 Chrome 打开 https://bigmodel.cn/glm-coding
2. 按 `F12` 打开开发者工具
3. 点击左上角的元素选择工具（箭头图标）
4. 点击页面上的「购买/订阅」按钮
5. 在 Elements 面板中右键该元素 → Copy → Copy selector
6. 粘贴到 `config.yaml` 的 `selectors.subscribe_button`
7. 同理获取支付弹窗的 `payment_dialog` 选择器

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `target.url` | 目标页面 URL | `https://bigmodel.cn/glm-coding` |
| `target.start_time` | 实际开始抢购时间 (HH:MM) | `9:59` |
| `schedule.time` | 脚本触发时间（提前预热） | `9:40` |
| `purchase.rounds` | 重试轮数 | `5` |
| `purchase.round_interval` | 轮次间隔（秒） | `5` |
| `purchase.max_retries` | 每轮内重试次数 | `3` |
| `purchase.retry_interval` | 重试间隔（秒） | `2` |
| `purchase.click_timeout` | 等待按钮超时（ms） | `5000` |
| `purchase.payment_wait_timeout` | 等待支付弹窗超时（ms） | `60000` |
| `browser.headless` | 无头模式（首次登录需 false） | `false` |
| `ntfy.enabled` | 是否启用推送通知 | `true` |

完整配置参考 `config_example.yaml`。

## 抢购流程

```
09:40:00  Scheduler 触发 → 启动浏览器，打开页面预热（避开高峰）
          等待直到 start_time...
09:59:00  Round 1: 刷新页面 → 点击订阅按钮 → 检测支付弹窗（最多 3 次重试）
09:59:xx  Round 2: 刷新页面 → 点击订阅按钮 → 检测支付弹窗
          ...共 5 轮，每轮间隔 5 秒
          支付弹窗出现 → 推送通知提醒扫码
          等待用户完成支付
          → 推送成功/失败通知
```

## 项目结构

```
├── main.py                 # 入口文件
├── config.yaml             # 运行配置（需自行创建）
├── config_example.yaml     # 配置模板
├── core/
│   ├── browser.py          # 浏览器控制
│   ├── purchaser.py        # 抢购核心流程
│   ├── notifier.py         # 消息推送
│   ├── scheduler.py        # 定时调度
│   └── config_loader.py    # 配置加载
├── utils/
│   ├── logger.py           # 日志工具
│   └── screenshot.py       # 截图工具
├── browser_data/           # 登录态数据（自动生成）
├── logs/                   # 日志文件（自动生成）
└── screenshots/            # 截图文件（自动生成）
```

## 注意事项

- 首次使用务必先运行 `python main.py --login` 完成登录
- 登录态过期后需重新登录，脚本会通过推送通知提醒
- 页面结构变化时需更新 `config.yaml` 中的 CSS 选择器
- `config.yaml` 已在 `.gitignore` 中排除，不会泄露隐私配置
