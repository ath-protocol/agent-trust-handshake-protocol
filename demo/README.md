[中文版 / Chinese Version](../zh/demo-README.md)

# ATH Protocol Demo
## ✨ V2 New Features
1. 🎮 **Interactive Authorization**: Two user interaction confirmations (pre-authorization + server-side secondary confirmation), fully compliant with the protocol specification
2. 🎬 **Cool Loading Effects**: Each step has loading animations and progress indicators for a better demo experience
3. 🧩 **Logic Separation**: Client and server are implemented completely independently with clear code structure, and can be extracted for standalone use
4. 📊 **Friendlier Interface**: Role differentiation, dividers, and color-coded labels make the workflow easier to understand
## How to Run
### 1. Run Locally in Console (Simplest)
Only requires Python 3.6+, no additional dependencies needed:
```bash
# Download the Demo file
wget https://raw.githubusercontent.com/ath-protocol/agent-trust-handshake-protocol/main/demo/ath_simple_demo.py
# Run directly
python ath_simple_demo.py
```
### 2. Run Online via GitHub (No Local Environment Needed)
You can run it online via GitHub Codespaces without any local environment:
1. Open the repository: https://github.com/ath-protocol/agent-trust-handshake-protocol
2. Click the green "Code" button and select "Codespaces"
3. Click "Create codespace on main"
4. Once the environment is ready, run in the terminal:
```bash
python demo/ath_simple_demo.py
```
## ❓ FAQ
### Q: The demo is in a single Python file — how does it implement both client and server?
A: Although it runs in the same file, **the client and server are two completely independent classes** with no coupling:
- 🔵 `Client` class: Fully implements all client logic, including identity management, handshake requests, permission requests, and business request sending
- 🟢 `Server` class: Fully implements all server logic, including identity verification, authorization confirmation, permission approval, and token issuance
The two interact only through agreed-upon JSON message formats, identical to how they would in a real network environment. In an actual deployment, these two classes would be deployed on different servers, communicating via HTTP/HTTPS.
### Q: Can the client/server logic be extracted separately?
A: Absolutely! The two classes are completely independent with no mutual dependencies. They can be directly copied out as a foundation for SDK and server middleware implementations.
## Demo Content
✅ Complete 9-step Trusted Handshake workflow demonstration:
1. Client sends handshake request
2. Server returns handshake response
3. Client sends identity proof
4. Server returns identity verification result
5. Client sends permission request
6. Server prompts user for authorization confirmation
7. User approves authorization
8. Server returns permission approval result
9. Handshake complete, access token issued
✅ Subsequent business request demonstrations:
- Query products API call
- Create order API call
## Demo Output
```
🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆
🎆                   ATH Trusted Handshake Protocol Interactive Demo               🎆
🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆🎆
📖 This demo is fully implemented according to the ATH protocol spec. Client and server logic are completely independent.
🤔 Show client and server implementation logic separately? (Y/N): Y
================================================================================
📌 Initialize Client
--------------------------------------------------------------------------------
⏳ Generating client DID identity and key pair /
✅ Generating client DID identity and key pair done!
   Client DID: did:ath:ai_shopping_assistant_001
   Client public key: client_public_key_ab...
================================================================================
📌 Initialize Server
--------------------------------------------------------------------------------
⏳ Loading server configuration and certificates ✅ Loading server configuration and certificates done!
   Server DID: did:ath:ecommerce_platform_001
   Server public key: server_public_key_fe...
🟣 ============================== [User Interaction] ============================== 🟣
📋 [Authorization Request] AI Shopping Assistant requests the following permissions:
   ✅ goods:read
   ✅ order:create
🤔 Approve authorization? (Y/N): Y
⏳ User signing authorization credential |
✅ User signing authorization credential done!
   Authorization credential: user_signature_7A3F2d...
================================================================================
📌 Begin 9-Step Trusted Handshake Workflow
--------------------------------------------------------------------------------
🔵 ============================== [Client Logic] ============================== 🔵
⏳ Generating handshake request message -
✅ Generating handshake request message done!
   Nonce: h00mGfW9tqkxEcQN
📤 Client -> Server: Sending handshake request
🟢 ============================== [Server Logic] ============================== 🟢
⏳ Validating client request format, generating server nonce ✅ Validating client request format, generating server nonce done!
⏳ Signing client nonce with private key |
✅ Signing client nonce with private key done!
   Server nonce: h9T68YWD0YnxwHUw
   Signature: sig_8F2d7A...
📤 Server -> Client: Returning handshake response
...
🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
🎉              Handshake Complete! Trusted Communication Channel Established      🎉
🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
```
## Features
- 🚀 Zero Dependencies: Only requires the Python standard library, no third-party packages needed
- 🎯 Minimalist: Clear code structure, explicit logic, easy to understand
- 🎬 Intuitive: Each step has clear output and animations, perfectly demonstrating the protocol workflow
- 🔗 Realistic: Fully implemented according to the ATH protocol specification, ready to run
- 🧩 Extensible: Client and server logic are completely independent and can be extracted for standalone use
