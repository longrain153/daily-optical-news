# 光通信行业每日简报（GitHub Actions + DeepSeek）

每天**北京时间约 07:30** 自动运行在云端：抓取行业外媒报道 → DeepSeek 按细分归类 +
翻译成中文 + 解读 → 邮件发送 + 发布成网页（含网页截图）。

## 细分领域
光传输（Ciena/Acacia/中兴/烽火/华为/长飞/领纤）· 光模块（旭创/新易盛/Coherent/Lumentum）·
AI光互联（英伟达/Meta/Google/Microsoft，CPO/硅光）· 光器件芯片（Coherent/Lumentum/源杰/光迅）·
卫星光通信 · 量子光通信

## 数据源
- The Next Platform（AI互联/CPO/数据中心）
- Light Reading（电信/光传输）
- Fierce Network（光纤/电信）
- DataCenterDynamics（数据中心/卫星）
- 翻译/归类/解读：DeepSeek `deepseek-chat`；网页截图：Playwright，托管本站

> 内容来自 RSS（订阅源），截图为独立尽力而为（个别站点有 WAF 会跳过截图，不影响内容）。
> 纯中国市场小厂家英文源覆盖有限，后续可补中文源。

## 在线版
- 最新：https://longrain153.github.io/daily-optical-news/

## Secrets
`DEEPSEEK_API_KEY`、`GMAIL_USER`、`GMAIL_APP_PASSWORD`、`MAIL_TO`
