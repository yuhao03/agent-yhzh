# agent-yhzh Web

Next.js 16 前端，包含两个权限边界明确的界面：

- `/`：普通用户智能助手，不显示任何内部知识资产。
- `/admin`：受服务端会话保护的知识成长工作台。

```bash
npm install
npm run dev
```

生产验证：

```bash
npm run lint
npm run build
npm run start
```

管理员密钥只由 Next.js 服务端读取，浏览器不会直接拿到 `ADMIN_API_KEY`，后端管理员接口也不会暴露给普通用户。
