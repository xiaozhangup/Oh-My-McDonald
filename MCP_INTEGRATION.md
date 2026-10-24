# MCP 接入说明

服务：https://mcp.mcd.cn。获取 Token：https://open.mcd.cn/mcp。

原生 MCP 客户端配置见 `mcp-config.example.json`，环境变量替换语法由各客户端处理。Python helper 自带 Streamable HTTP 传输，读取 `MCD_MCP_TOKEN`，或用户显式选择的 Codex TOML 中 `[mcp_servers.mcd-mcp].http_headers.Authorization`。脚本固定官方域名，执行 initialize 与 initialized 通知，支持 JSON/SSE、会话 ID 和协商协议版本。

## 使用的实际工具

| 工具 | 用途 |
| --- | --- |
| query-nearby-stores | 收藏或城市关键词搜索 |
| query-meals | 门店菜单，显示价格字符串以元为单位 |
| query-meal-detail | 子项编码、默认选择和数量约束 |
| query-store-coupons | 指定门店可用券、绑定商品 |
| query-my-coupons | 分页查询本人卡包，最多5页，每页200 |
| calculate-price | 实际应付，主价格字段以分为单位 |
| campaign-calendar | 已发布活动，兼容 articleDto 文章标题 |
| list-nutrition-foods | 标准份量营养表，TOON 格式 |
| order-list | 近期完成订单，用于待确认导入 |

到店场景统一 `orderType=1, beType=1, storeCode=实际门店编码`，省略 `beCode`。套餐报价发送 `items[].productCode`、正整数数量及字符串 `roundList[].round`，子项用 `comboItemList[].code/quantity`。

主金额使用 `data.price`，不从商品小计相加推断最终应付。`enjoyed` 的已应用名称可展示，`enjoyable` 不纳入已享优惠。仅在同商品编码与同份量成立时比较券与普通报价；不同编码的券套餐另建篮子展示。

## 隐私与运行方式

请求由用户当前对话触发，串行执行，单次抽取最多6个候选、门店比较最多3家，不做轮询。连接失败或业务错误停止当前查询，不自动重试。白名单没有任何创建订单、支付、领券或兑换工具。

运行不输出 Token 或原始错误响应。只读查询的数据在内存中处理，待确认和本地记录写入0600文件。输出图片与摘要通过字段白名单构造，券 ID、券码、订单号和详细地址均不进入公开卡片。
