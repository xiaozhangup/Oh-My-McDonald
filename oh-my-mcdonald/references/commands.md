# 命令和输入

以下从仓库根目录运行。`S=oh-my-mcdonald/scripts/oh_my_mcdonald.py` 只是缩短示例路径。

```bash
S=oh-my-mcdonald/scripts/oh_my_mcdonald.py
python "$S" stores --city 武汉 --keyword 东澜岸
python "$S" menu --store 1960151 --contains 汉堡
python "$S" detail --store 1960151 --code 9900005456
```

凭证在当前进程的 `MCD_MCP_TOKEN` 中，或在子命令前加 `--codex-config /本机/路径/config.toml`。脚本固定请求 https://mcp.mcd.cn。

篮子文件：

```json
{"items":[{"productCode":"实际查询取得的编码","quantity":1}]}
```

省略 `roundList` 时取当前门店的默认选项；默认选项未满足必选数量时返回错误。手动选择时传完整必选组：

```json
{"items":[{"productCode":"9900005456","quantity":1,"roundList":[
  {"round":"1","comboItemList":[{"code":"1440","quantity":1}]},
  {"round":"2","comboItemList":[{"code":"4810","quantity":1}]},
  {"round":"3","comboItemList":[{"code":"3071","quantity":1}]}
]}]}
```

此示例为2026-10-24验证的麦辣鸡腿汉堡、中薯条和无糖可口可乐中杯；套餐的轮次 ID 是字符串。先查详情确认当前可售，餐品特制选项暂由客户端另外解释，脚本首版仅支持完整标准份量与套餐子项选择。

```bash
python "$S" --out output quote --store 1960151 --basket examples/basket.json
python "$S" --out output compare --stores 1960151 1960213 --basket examples/basket.json --locations private/stores.json
python "$S" --out output nutrition --store 1960151 --basket examples/basket.json
python "$S" --out output coupons --store 1960151
python "$S" --out output calendar --month 2026-10
```

`private/stores.json` 为 `stores` 命令的完整 JSON 输出，提供真实店名；可以将命令标准输出重定向到该文件。比较的门店使用搜索返回的实际编码。当前比价最多3家；自动优惠测试范围为单个数量1的同编码商品最多3张券，其他篮子采用官方自动优惠。券绑定的不同套餐编码用新篮子单独报价，按份量列清后由用户选择。

候选文件：

```json
{"candidates":[{"items":[{"productCode":"1100","quantity":1}]},{"items":[{"productCode":"9900005456","quantity":1}]}]}
```

```bash
python "$S" draw --store 1960151 --candidates examples/candidates.json --mode explore --budget 35 --exclude 可乐
```

`--mode` 为 `random`、`save`、`explore`，分别对应随便抽、省钱抽、探索抽。关键词针对展开后的子项，`可乐`会同时排除无糖可乐。预算为总应付金额，先筛选后抽取。结果仅覆盖输入的最多6个候选。

```bash
python "$S" --out private import-preview
# 用户确认 pending 中第0条的本人食用编码后：
python "$S" confirm --pending private/pending-orders.json --entry 0 --foods 1440 4810
# 用户明确确认去过该店时，可以追加 --visit。
python "$S" record --kind food --code 1100 --name 巨无霸 --date 2026-10-24
python "$S" remove --kind food --code 1100
python "$S" album
```

图鉴的可选目录 JSON 为 `{"foods":[{"code":"1100","name":"巨无霸"}]}`，通过 `album --catalog path.json` 输入。每页最多12个图鉴项。编码按规格区分，首版不自动合并同名餐品；图片模型用于类别示意，套餐食用记录使用子项编码。

`--state /路径/records.json` 可隔离多个用户，必须在子命令前传入。脚本没有账户服务器，记录保存在本机。公开图片可转发；带详细食用历史的本地文件由用户保管。

长内容自动拆成多张分享图，结果的 `pages` 给出全部图片路径，`image` 为第一页，`summary` 为完整数据。

离线查看原创模型库：

```bash
python "$S" --out output models
```
