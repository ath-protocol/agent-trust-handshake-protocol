# ATH可信握手协议 - 中文版
> 🎯 通俗易懂版，非技术人员也能看懂
---
## 📋 文档说明
本文档是ATH协议的中文版，把原本分散在十几个技术文档里的内容整合到一起，用最容易理解的语言解释协议的所有核心内容。
> 💡 专业提示：程序实际执行时用的是`spec/openapi.yaml`和`schema/0.1/schema.json`这两个机器可读文件，本文档是给人看的说明书。
---

## 📖 1. 协议概述
---
## 概述

ATH（Agent Trust Handshake Protocol，代理信任握手协议）是一种轻量级、去中心化的应用层安全协议，用于在 AI 代理与外部服务（第三方应用、其他代理等）之间建立可信连接。

ATH 基于 **OAuth 2.0** 这一广泛部署的第三方授权框架构建。它在 OAuth 之上添加了代理身份层和应用端授权层，实现了**可信握手** — 这是本协议的核心安全原则。

## 设计原则

1. **可信握手**：应用端和用户端的授权均为强制要求，二者缺一不可。
2. **去中心化**：支持任意代理连接到任意服务，无需中心化权威机构。
3. **开放性**：不绑定单一平台、供应商或技术栈。
4. **轻量级**：仅专注于信任握手和授权，不涉及业务逻辑或传输协议。
5. **渐进式采纳**：服务可以分阶段采纳 ATH，从零更改的网关模式到完整的原生实现。

## 协议定位

ATH 运行在应用层，位于面向用户的操作与通信协议之间：

```
┌─────────────────────────────────────┐
│  用户操作（CLI、UI、技能）           │  用户与代理交互
├─────────────────────────────────────┤
│  ATH（信任与授权）                   │  代理身份 + 可信握手
├─────────────────────────────────────┤
│  A2A / MCP（协作）                   │  代理间 / 代理与工具
├─────────────────────────────────────┤
│  HTTPS / TLS（传输）                 │  安全传输
└─────────────────────────────────────┘
```

ATH 不与 MCP 或 A2A 竞争，而是通过提供这些协议目前缺乏的信任层来与之互补。

## 部署模型

ATH 支持两种部署模型。两者均为有效的协议合规方案。

### 网关模式

一个 ATH 合规的网关位于代理与服务之间。服务提供方无需实现 ATH — 网关使用任意 OAuth 桥接实现代表其执行可信握手。

```
代理 → ATH 网关 → 服务提供方（无需更改）
```

### 原生模式

服务直接实现 ATH 端点，以实现更紧密的集成。

```
代理 → 服务提供方（ATH 原生）
```

两种模型执行相同的可信握手。网关模式更易部署；原生模式赋予服务更多控制权。详细架构图请参见[架构](/zh/docs/learn/architecture)。


## 🪪 2. 身份认证规范
---
## 代理身份（Agent_ID）

每个代理必须（MUST）拥有唯一且可验证的身份。

**格式**：基于 URI 的标识符，遵循以下模式：

```
https:///.well-known/agent.json
```

**示例**：
```
https://travel-agent.example.com/.well-known/agent.json
https://coding-assistant.example.com/.well-known/agent.json
```

## 代理身份文档

代理必须（MUST）在其 `agent_id` URI 上发布一个 JSON 文档：

```json
{
  "ath_version": "0.1",
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "name": "TravelBot",
  "developer": {
    "name": "Example Corp",
    "id": "dev-example-12345",
    "contact": "security@example.com"
  },
  "capabilities": ["flight-search", "hotel-booking", "itinerary-planning"],
  "public_key": ""
}
```

### 必填字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `ath_version` | string | 协议版本（例如 `"0.1"`） |
| `agent_id` | string | 该代理的规范 URI |
| `name` | string | 人类可读的代理名称 |
| `developer` | object | 开发者信息 |
| `developer.name` | string | 开发者或组织名称 |
| `developer.id` | string | 开发者标识符 |
| `public_key` | string/object | 用于证明验证的 JWK 或 PEM |

### 可选字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `developer.contact` | string | 安全联系邮箱 |
| `capabilities` | string[] | 代理能力列表 |

## 服务身份（App_ID）

服务通过其现有标识符进行识别：
- **客户端应用**：包名（例如 `com.example.mail`）
- **服务端服务**：URI（例如 `https://api.example.com`）

## 代理证明

代理使用签名的 JWT（代理证明令牌）来证明其身份。

### JWT 头部

```json
{
  "alg": "ES256",
  "typ": "JWT",
  "kid": ""
}
```

### JWT 载荷

```json
{
  "iss": "https://travel-agent.example.com",
  "sub": "",
  "aud": "",
  "iat": 1720000000,
  "exp": 1720003600,
  "capabilities": ["flight-search"]
}
```

### 必需声明

| 声明 | 描述 |
|-------|-------------|
| `iss` | 签发者 — 代理的域名 |
| `sub` | 主体 — 完整的 `agent_id` URI |
| `aud` | 受众 — 目标服务或网关 URL |
| `iat` | 签发时间 — 时间戳 |
| `exp` | 过期时间 — 必须（MUST）存在 |

### 验证

验证方（网关或服务）：
1. 从 `agent_id` URI 获取代理的身份文档
2. 提取公钥
3. 使用公钥验证 JWT 签名
4. 验证 `exp`（未过期）和 `aud`（与验证方的 URL 匹配）
5. 实现者必须（MUST）拒绝已过期或受众不匹配的证明


## 🤝 3. 握手流程规范
---
协议包含两个不同的阶段。阶段 A 是**一次性设置**。阶段 B 在**运行时针对每个用户**发生。

## 阶段 A：应用端授权

```
代理开发者                         ATH 实现者
      │                            （网关或服务）
      │                                    │
      │  1. 注册代理                        │
      │  （agent_id、证明、                  │
      │   请求的能力）                       │
      ├───────────────────────────────────►│
      │                                    │
      │                          2. 验证代理身份
      │                             审查能力
      │                             批准/拒绝
      │                                    │
      │  3. 注册响应                        │
      │  （client_id、已批准的范围、          │
      │   批准过期时间）                     │
      │◄───────────────────────────────────┤
```

**结果**：代理以特定能力限制进入已批准的注册表。此状态持续有效直至被吊销。

## 阶段 B：用户端授权

```
用户         代理        ATH 实现者           服务
 │             │                  │                │
 │  "执行 X"  │                  │                │
 ├────────────►│                  │                │
 │             │                  │                │
 │             │  4. 请求         │                │
 │             │  访问权限        │                │
 │             ├─────────────────►│                │
 │             │                  │                │
 │             │        5. 验证代理身份            │
 │             │           检查审批状态            │
 │             │                  │                │
 │             │        6. 发起 OAuth 流程         │
 │             │                  ├───────────────►│
 │             │                  │                │
 │  7. OAuth 授权同意页面         │                │
 │◄──────────────────────────────────────────────┤
 │                                │                │
 │  8. 用户批准                   │                │
 ├──────────────────────────────────────────────►│
 │             │                  │                │
 │             │                  │  9. OAuth 令牌 │
 │             │                  │◄───────────────┤
 │             │                  │                │
 │             │  10. 范围交集                     │
 │             │      与令牌绑定                   │
 │             │                  │                │
 │             │  11. ATH 访问令牌                 │
 │             │◄─────────────────┤                │
 │             │                  │                │
 │             │  12. API 调用（ATH 令牌）         │
 │             ├─────────────────►│                │
 │             │                  │  13. 代理转发/  │
 │             │                  │  服务           │
 │             │                  ├───────────────►│
 │             │                  │  14. 响应      │
 │             │                  │◄───────────────┤
 │             │  15. 结果       │                │
 │             │◄─────────────────┤                │
 │  16. 回答  │                  │                │
 │◄────────────┤                  │                │
```

在网关模式中，"ATH 实现者"是网关，"服务"是上游服务提供方。在原生模式中，"ATH 实现者"和"服务"是同一实体。

## 范围交集（步骤 10）

任何访问令牌的有效范围是以下三个集合的**交集**：

```
有效范围 = 代理已批准的范围 ∩ 用户已同意的范围 ∩ 请求的范围
```

详情请参见[范围交集](/zh/specification/0.1/client/scope-intersection)。


## 🔐 4. 安全加密规范
---
## 代理证明验证

- 代理证明 JWT 必须（MUST）通过代理在其 `agent_id` URI 上发布的公钥进行验证
- JWT 必须（MUST）包含过期时间（`exp`）和受众（`aud`）
- 实现者必须（MUST）拒绝已过期或受众不匹配的证明

## 令牌绑定

- ATH 访问令牌必须（MUST）绑定到特定的 `(agent_id, user_id, provider_id, scopes)` 元组
- 一个代理获取的令牌禁止（MUST NOT）被另一个代理使用
- 为一个用户获取的令牌禁止（MUST NOT）被另一个用户使用

## OAuth 安全性

- 所有 OAuth 授权请求必须（MUST）使用 PKCE（[RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)）及 S256 挑战方法
- 令牌交换请求必须（MUST）使用 `application/x-www-form-urlencoded` 内容类型，遵循 [RFC 6749 §4.1.3](https://datatracker.ietf.org/doc/html/rfc6749#section-4.1.3)
- 服务提供方的 OAuth 客户端密钥必须（MUST）安全存储，且绝不暴露给代理或用户
- 从 OAuth 流程获取的服务提供方令牌（access_token、refresh_token）必须（MUST）存储在服务端，且绝不发送给代理

## 传输安全

- 所有 ATH 通信必须（MUST）使用 HTTPS（TLS 1.2+）
- 实现者建议（SHOULD）验证上游服务的 TLS 证书
- 在高安全性环境中，mTLS 是可选的（OPTIONAL）（v2 考虑事项）

## 审计日志

实现者建议（SHOULD）记录所有授权决策：

```json
{
  "timestamp": "2026-04-10T12:00:00Z",
  "event": "access_granted",
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "user_id": "user-12345",
  "provider_id": "example-mail",
  "requested_scopes": ["mail:read", "mail:send"],
  "effective_scopes": ["mail:read"],
  "denied_scopes": ["mail:send"],
  "denial_reason": "agent not approved for mail:send"
}
```

## 速率限制与滥用防护

- 实现者建议（SHOULD）执行每代理的速率限制
- 具有异常请求模式的代理建议（SHOULD）被标记并可能被暂停
- 代理注册表建议（SHOULD）支持对已泄露代理的吊销


## ⚖️ 5. 权限控制规范
---
## 定义

任何 ATH 访问令牌的有效范围必须（MUST）按以下方式计算：

```
有效范围 = 代理已批准的范围 ∩ 用户已同意的范围 ∩ 请求的范围
```

其中：
- **代理已批准的范围**：ATH 实现者在阶段 A 注册期间为代理批准的范围集合
- **用户已同意的范围**：用户在阶段 B OAuth 授权同意流程中授予的范围集合
- **请求的范围**：代理在授权请求中请求的范围集合

## 示例

```
代理已批准的范围：     mail:read, mail:send
用户已同意的范围：     mail:read, mail:send, mail:delete
代理请求的范围：       mail:read
────────────────────────────────────────────────
有效范围：             mail:read
```

## 要求

1. 实现者在签发任何 ATH 访问令牌之前，必须（MUST）计算范围交集
2. 令牌响应必须（MUST）包含 `scope_intersection` 分解信息
3. 实现者禁止（MUST NOT）签发包含计算交集之外范围的令牌
4. 如果交集为空，实现者禁止（MUST NOT）签发令牌

## 令牌响应格式

```json
{
  "access_token": "ath_tk_xxxxxxxx",
  "token_type": "Bearer",
  "expires_in": 3600,
  "effective_scopes": ["mail:read"],
  "provider_id": "example-mail",
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "scope_intersection": {
    "agent_approved": ["mail:read"],
    "user_consented": ["mail:read", "mail:send"],
    "effective": ["mail:read"]
  }
}
```

`scope_intersection` 字段提供了有效范围如何推导出来的完全透明信息。


## 🎫 6. 令牌管理规范
---
## 令牌交换（阶段 B，用户同意后）

**`POST /ath/token`**

用户完成 OAuth 授权同意流程后，代理用授权码交换 ATH 访问令牌。实现者计算范围交集并绑定令牌。

## 请求

```json
{
  "grant_type": "authorization_code",
  "client_id": "ath_travelbot_001",
  "client_secret": "ath_secret_xxxxx",
  "code": "",
  "ath_session_id": "ath_sess_abc123"
}
```

### 请求字段

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `grant_type` | string | 是 | 必须为 `"authorization_code"` |
| `client_id` | string | 是 | 代理的客户端 ID |
| `client_secret` | string | 是 | 代理的客户端密钥 |
| `code` | string | 是 | 回调中收到的 OAuth 授权码 |
| `ath_session_id` | string | 是 | 授权步骤返回的会话 ID |

## 响应

```json
{
  "access_token": "ath_tk_xxxxxxxx",
  "token_type": "Bearer",
  "expires_in": 3600,
  "effective_scopes": ["mail:read"],
  "provider_id": "example-mail",
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "scope_intersection": {
    "agent_approved": ["mail:read"],
    "user_consented": ["mail:read", "mail:send"],
    "effective": ["mail:read"]
  }
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `access_token` | string | ATH 访问令牌 |
| `token_type` | string | 始终为 `"Bearer"` |
| `expires_in` | number | 令牌有效期（秒） |
| `effective_scopes` | string[] | 计算得出的有效范围 |
| `provider_id` | string | 此令牌对应的服务提供方 |
| `agent_id` | string | 此令牌绑定的代理 |
| `scope_intersection` | object | 范围交集的完整分解 |
| `scope_intersection.agent_approved` | string[] | 服务为该代理批准的范围 |
| `scope_intersection.user_consented` | string[] | 用户同意的范围 |
| `scope_intersection.effective` | string[] | 交集（有效权限） |

## 行为

- 响应必须（MUST）包含 `scope_intersection` 分解信息
- 令牌必须（MUST）绑定到特定的 `(agent_id, user_id, provider_id, scopes)` 元组
- 如果范围交集为空，实现者禁止（MUST NOT）签发令牌


## ✅ 7. 授权决策规范
---
## 授权请求（阶段 B）

**`POST /ath/authorize`**

发起用户端授权流程。实现者验证代理已注册且已获批准，然后为用户发起 OAuth 授权同意流程。

## 请求

```json
{
  "client_id": "ath_travelbot_001",
  "agent_attestation": "",
  "provider_id": "example-mail",
  "scopes": ["mail:read"],
  "user_redirect_uri": "https://travel-agent.example.com/callback",
  "state": "",
  "resource": "https://api.example.com/v1"
}
```

### 请求字段

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `client_id` | string | 是 | 注册时获取的代理客户端 ID |
| `agent_attestation` | string | 是 | 新鲜的签名 JWT，用于证明代理身份 |
| `provider_id` | string | 是 | 要授权的服务提供方 |
| `scopes` | string[] | 是 | 要请求的范围（必须在已批准范围内） |
| `user_redirect_uri` | string | 否 | OAuth 授权同意后的重定向地址 |
| `state` | string | 否 | 用于 CSRF 保护的不透明状态值 |
| `resource` | string | 否 | 目标资源服务器 URI（[RFC 8707](https://datatracker.ietf.org/doc/html/rfc8707)） |

## 响应

```json
{
  "authorization_url": "https://example.com/oauth/authorize?client_id=...&scope=mail:read&code_challenge=...&code_challenge_method=S256&state=...",
  "ath_session_id": "ath_sess_abc123"
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `authorization_url` | string | 用户应被引导至的 OAuth 授权同意 URL |
| `ath_session_id` | string | 用于令牌交换步骤的会话标识符 |

## 行为

- 实现者必须（MUST）验证代理已注册且 `agent_status` 为 `"approved"`
- 实现者必须（MUST）验证证明 JWT 有效
- 实现者必须（MUST）检查代理已获得所请求服务提供方的批准
- 请求的范围必须（MUST）在代理针对该服务提供方已批准的范围内
- `authorization_url` 必须（MUST）包含 PKCE 参数（[RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)）— `code_challenge` 和 `code_challenge_method=S256`
- 对应的 `code_verifier` 存储在服务端，在令牌交换时发送
- 代理将用户引导至 `authorization_url`
- 授权同意后，OAuth 回调由 ATH 实现者处理


## 📝 8. 服务注册规范
---
## 代理注册（阶段 A）

**`POST /ath/agents/register`**

向 ATH 实现者注册一个新代理。实现者验证代理的身份，并根据其审批策略评估请求的能力。

## 请求

```json
{
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "agent_attestation": "",
  "developer": {
    "name": "Example Corp",
    "id": "dev-example-12345"
  },
  "requested_providers": [
    {
      "provider_id": "example-mail",
      "scopes": ["mail:read", "mail:send"]
    }
  ],
  "purpose": "Travel planning assistant",
  "redirect_uris": ["https://travel-agent.example.com/callback"]
}
```

### 请求字段

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `agent_id` | string | 是 | 代理的规范 URI |
| `agent_attestation` | string | 是 | 证明代理身份的签名 JWT |
| `developer` | object | 是 | 开发者信息 |
| `developer.name` | string | 是 | 开发者或组织名称 |
| `developer.id` | string | 是 | 开发者标识符 |
| `requested_providers` | array | 是 | 请求的服务提供方和范围 |
| `requested_providers[].provider_id` | string | 是 | 服务提供方标识符 |
| `requested_providers[].scopes` | string[] | 是 | 该服务提供方请求的范围 |
| `purpose` | string | 否 | 代理用途的人类可读描述 |
| `redirect_uris` | string[] | 否 | OAuth 回调 URI |

## 响应（成功）

```json
{
  "client_id": "ath_travelbot_001",
  "client_secret": "ath_secret_xxxxx",
  "agent_status": "approved",
  "approved_providers": [
    {
      "provider_id": "example-mail",
      "approved_scopes": ["mail:read"],
      "denied_scopes": ["mail:send"],
      "denial_reason": "Send capability requires additional review"
    }
  ],
  "approval_expires": "2027-01-01T00:00:00Z"
}
```

### 响应字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `client_id` | string | 此次注册的唯一标识符 |
| `client_secret` | string | 用于认证令牌交换请求的密钥 |
| `agent_status` | string | `"approved"`、`"pending"` 或 `"denied"` |
| `approved_providers` | array | 各服务提供方的审批结果 |
| `approved_providers[].approved_scopes` | string[] | 已批准的范围 |
| `approved_providers[].denied_scopes` | string[] | 被拒绝的范围 |
| `approved_providers[].denial_reason` | string | 拒绝原因（如有） |
| `approval_expires` | string | ISO 8601 格式的过期时间戳 |

## 行为

- 实现者可以（MAY）批准请求能力的**子集**
- 代理必须（MUST）遵守已批准的范围限制
- 对同一 `agent_id` 的重复注册建议（SHOULD）返回 `409 Conflict`


## 🚫 9. 令牌吊销规范
---
## 令牌吊销

**`POST /ath/revoke`**

吊销一个 ATH 访问令牌，使其立即不可用。

## 请求

```json
{
  "client_id": "ath_travelbot_001",
  "token": "ath_tk_xxxxxxxx"
}
```

### 请求字段

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `client_id` | string | 是 | 代理的客户端 ID |
| `token` | string | 是 | 要吊销的 ATH 访问令牌 |

## 响应

成功吊销后返回 `200 OK`。

## 行为

- 令牌在吊销后立即不可用
- 使用已吊销令牌的后续 API 调用必须（MUST）被拒绝
- 代理、用户（通过管理界面）或管理员均可吊销令牌
- 吊销操作建议（SHOULD）记录审计日志


## 🏗️ 10. 数据结构定义
---
本页面记录了 ATH 协议 API 使用的所有请求和响应 Schema。

规范的机器可读 Schema 提供以下格式：
- [JSON Schema](https://github.com/ath-protocol/agent-trust-handshake-protocol/blob/main/schema/0.1/schema.json)（JSON Schema 2020-12）— 用于 SDK 代码生成和验证
- [OpenAPI 3.1 YAML](https://github.com/ath-protocol/agent-trust-handshake-protocol/blob/main/spec/openapi.yaml) — 用于 API 文档和测试

## 发现

### DiscoveryDocument

由 `GET /.well-known/ath.json` 返回。

```json
{
  "ath_version": "0.1",
  "gateway_id": "ath-gateway.example.com",
  "agent_registration_endpoint": "https://ath-gateway.example.com/ath/agents/register",
  "supported_providers": [ProviderInfo]
}
```

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `ath_version` | string | 是 | 协议版本 |
| `gateway_id` | string | 是 | 网关标识符 |
| `agent_registration_endpoint` | string (URI) | 是 | 代理注册 URL |
| `supported_providers` | ProviderInfo[] | 是 | 可用的服务提供方 |

### ProviderInfo

```json
{
  "provider_id": "example-mail",
  "display_name": "Example Mail",
  "categories": ["email", "productivity"],
  "available_scopes": ["mail:read", "mail:send", "mail:delete"],
  "auth_mode": "OAUTH2",
  "agent_approval_required": true
}
```

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `provider_id` | string | 是 | 唯一的服务提供方标识符 |
| `display_name` | string | 是 | 人类可读的名称 |
| `categories` | string[] | 否 | 服务提供方分类 |
| `available_scopes` | string[] | 是 | 可请求的范围 |
| `auth_mode` | string | 是 | 认证模式（例如 `"OAUTH2"`） |
| `agent_approval_required` | boolean | 是 | 是否需要注册 |

## 注册

### AgentRegistrationRequest

发送至 `POST /ath/agents/register`。

```json
{
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "agent_attestation": "",
  "developer": {
    "name": "Example Corp",
    "id": "dev-example-12345"
  },
  "requested_providers": [

  ],
  "purpose": "Travel planning assistant",
  "redirect_uris": ["https://travel-agent.example.com/callback"]
}
```

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `agent_id` | string (URI) | 是 | 代理的规范 URI |
| `agent_attestation` | string (JWT) | 是 | 签名的证明令牌 |
| `developer.name` | string | 是 | 开发者名称 |
| `developer.id` | string | 是 | 开发者标识符 |
| `requested_providers` | array | 是 | 请求的服务提供方和范围 |
| `purpose` | string | 否 | 人类可读的用途说明 |
| `redirect_uris` | string[] | 否 | OAuth 回调 URI |

### AgentRegistrationResponse

```json
{
  "client_id": "ath_travelbot_001",
  "client_secret": "ath_secret_xxxxx",
  "agent_status": "approved",
  "approved_providers": [ProviderApproval],
  "approval_expires": "2027-01-01T00:00:00Z"
}
```

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `client_id` | string | 唯一的注册标识符 |
| `client_secret` | string | 令牌交换的密钥 |
| `agent_status` | `"approved"` \| `"pending"` \| `"denied"` | 注册状态 |
| `approved_providers` | ProviderApproval[] | 各服务提供方的审批结果 |
| `approval_expires` | string (ISO 8601) | 过期时间戳 |

### ProviderApproval

```json
{
  "provider_id": "example-mail",
  "approved_scopes": ["mail:read"],
  "denied_scopes": ["mail:send"],
  "denial_reason": "Send capability requires additional review"
}
```

## 授权

### AuthorizationRequest

发送至 `POST /ath/authorize`。

```json
{
  "client_id": "ath_travelbot_001",
  "agent_attestation": "",
  "provider_id": "example-mail",
  "scopes": ["mail:read"],
  "user_redirect_uri": "https://travel-agent.example.com/callback",
  "state": "",
  "resource": "https://api.example.com/v1"
}
```

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `client_id` | string | 是 | 代理的客户端 ID |
| `agent_attestation` | string (JWT) | 是 | 新鲜的证明令牌 |
| `provider_id` | string | 是 | 要授权的服务提供方 |
| `scopes` | string[] | 是 | 要请求的范围（需在已批准范围内） |
| `user_redirect_uri` | string (URI) | 否 | 授权同意后的重定向地址 |
| `state` | string | 否 | CSRF 保护状态值 |
| `resource` | string (URI) | 否 | 目标资源服务器（[RFC 8707](https://datatracker.ietf.org/doc/html/rfc8707)） |

### AuthorizationResponse

```json
{
  "authorization_url": "https://example.com/oauth/authorize?...&code_challenge=...&code_challenge_method=S256",
  "ath_session_id": "ath_sess_abc123"
}
```

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `authorization_url` | string (URI) | 包含 PKCE 参数的 OAuth 授权同意 URL |
| `ath_session_id` | string | 用于令牌交换的会话 ID |

## 令牌

### TokenExchangeRequest

发送至 `POST /ath/token`。

```json
{
  "grant_type": "authorization_code",
  "client_id": "ath_travelbot_001",
  "client_secret": "ath_secret_xxxxx",
  "code": "",
  "ath_session_id": "ath_sess_abc123"
}
```

### TokenResponse

```json
{
  "access_token": "ath_tk_xxxxxxxx",
  "token_type": "Bearer",
  "expires_in": 3600,
  "effective_scopes": ["mail:read"],
  "provider_id": "example-mail",
  "agent_id": "https://travel-agent.example.com/.well-known/agent.json",
  "scope_intersection": {
    "agent_approved": ["mail:read"],
    "user_consented": ["mail:read", "mail:send"],
    "effective": ["mail:read"]
  }
}
```

### ScopeIntersection

```json
{
  "agent_approved": ["mail:read"],
  "user_consented": ["mail:read", "mail:send"],
  "effective": ["mail:read"]
}
```

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `agent_approved` | string[] | 服务为该代理批准的范围 |
| `user_consented` | string[] | 用户同意的范围 |
| `effective` | string[] | 交集（有效权限） |

## 吊销

### TokenRevocationRequest

发送至 `POST /ath/revoke`。

```json
{
  "client_id": "ath_travelbot_001",
  "token": "ath_tk_xxxxxxxx"
}
```

## 错误

### ATHError

所有错误响应遵循以下结构：

```json
{
  "code": "INVALID_ATTESTATION",
  "message": "Agent attestation JWT has expired",
  "details": 
}
```

| 错误码 | HTTP 状态码 | 描述 |
|------|-------------|-------------|
| `INVALID_ATTESTATION` | 401 | 代理证明 JWT 验证失败 |
| `AGENT_NOT_REGISTERED` | 403 | 代理必须先注册才能授权 |
| `AGENT_UNAPPROVED` | 403 | 代理注册被拒绝 |
| `PROVIDER_NOT_APPROVED` | 403 | 代理未获得该服务提供方的批准 |
| `SCOPE_NOT_APPROVED` | 403 | 代理未获得所请求范围的批准 |
| `SESSION_NOT_FOUND` | 400 | 未找到 OAuth 会话 |
| `SESSION_EXPIRED` | 400 | OAuth 会话已过期 |
| `STATE_MISMATCH` | 400 | OAuth state 参数不匹配 |
| `TOKEN_INVALID` | 401 | ATH 访问令牌无效 |
| `TOKEN_EXPIRED` | 401 | ATH 访问令牌已过期 |
| `TOKEN_REVOKED` | 401 | ATH 访问令牌已被吊销 |
| `AGENT_IDENTITY_MISMATCH` | 403 | 请求中的代理 ID 与令牌绑定不匹配 |
| `PROVIDER_MISMATCH` | 403 | 请求中的服务提供方与令牌绑定不匹配 |
| `USER_DENIED` | 403 | 用户拒绝了 OAuth 授权同意 |
| `OAUTH_ERROR` | 502 | 上游 OAuth 提供方返回错误 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |


---
## 🎯 给非技术人员的通俗总结
### 一句话说清楚ATH是干嘛的
ATH就是AI世界的"身份证+门禁系统+公证处"三合一，让AI之间的交互像人与人握手一样可信。
### 核心解决的问题
以前AI访问数据就像陌生人随便进你家拿东西，没人管，出了问题也找不到人。有了ATH之后：
1. 所有AI都有唯一身份证，无法伪造
2. AI要访问任何资源都要经过"用户同意+服务同意"双重验证
3. 所有操作都有记录，出了问题可以追溯
### 最核心的8步握手流程
1. AI提前注册，拿到身份证
2. AI要访问服务时，提交申请说"我是谁，要干嘛"
3. 系统验证AI的身份证是真的
4. 系统验证要访问的服务是合法的
5. 问用户：同不同意这个AI访问？
6. 问服务：同不同意给这个AI提供服务？
7. 双方都同意，给AI发临时通行证
8. AI用通行证访问服务，全程记录
### 安全保障
- 所有通信都加密，没人能窃听
- 通行证用完就失效，不会被冒用
- 所有操作都留痕，无法篡改
---
## 📚 版本信息
- 协议版本：v0.1
- 中文翻译版：通俗易懂版
- 更新时间：2024年5月
