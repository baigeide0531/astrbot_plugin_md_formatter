# AstrBot 插件：MD 格式清理

解决 AstrBot + **OneBot v11 (NapCat)** 接入 QQ 时，AI 输出中的 markdown
无法渲染、符号裸露、表格乱码、代码块异常的问题。

## 效果对比

**转换前（QQ 里看到的）**
```
# 今日天气

**北京**：晴，**35℃**
- 空气：良
- 建议：多喝水

| 城市 | 温度 |
| --- | --- |
| 北京 | 35℃ |
| 上海 | 32℃ |
```

**转换后（QQ 里看到的）**
```
今日天气

北京：晴，35℃
· 空气：良
· 建议：多喝水

城市｜温度
北京｜35℃
上海｜32℃
```

## 安装

1. 把整个 `astrbot-plugin-md-formatter` 文件夹放入 AstrBot 的插件目录
   （`data/plugins/` 或通过 WebUI 上传 zip）。
2. 在 AstrBot 管理面板 **重启/启用** 该插件。
3. 无需额外依赖（仅用 Python 标准库 + AstrBot API）。

## 配置

在 AstrBot 插件配置页可调：

| 配置项 | 说明 | 默认 |
|---|---|---|
| `enabled` | 总开关 | `true` |
| `keep_code_block` | 代码块保留原文并加边框 | `true` |
| `apply_to_platforms` | 生效平台列表 | `["aiocqhttp"]` |

> 默认只处理 `aiocqhttp`（即 OneBot v11 / NapCat），不影响 Telegram 等
> 原生支持 markdown 渲染的平台。

## 工作原理

通过注册 AstrBot 的 `on_decorating_result`（发送消息前）事件钩子，
遍历消息链中的所有 `Plain` 文本组件，将 markdown 语法转换为 QQ 可读文本：

- 标题 `# ##` → 去掉井号
- 加粗 `**x**` / 斜体 `*x*` / 删除线 `~~x~~` → 去符号
- 行内代码 `` `x` `` → 去掉反引号
- 代码块 ` ``` ` → 保留原文，加 `┌─ 代码 ──` 边框
- 无序列表 `-` → `·`；有序列表 `1.` → `1.`；任务列表 → `☑/☐`
- 表格 `| a | b |` → `a｜b` 行列文本
- 链接 `[文字](url)` → `文字 (url)`；图片 → `[图片]`
- 引用 `>` → `│`；分割线 `---` → `━━`

## 文件结构

```
astrbot-plugin-md-formatter/
├── main.py            # 插件核心（Star 类 + markdown 转换器）
├── metadata.yaml      # 插件元信息
├── _conf_schema.json  # 配置项定义
└── README.md
```

## 卸载

在 AstrBot 中停用并删除该插件文件夹即可，无残留数据。

---

## 反馈与联系

如有问题、建议或反馈，欢迎通过邮箱联系：

📧 **1125835067@qq.com**
