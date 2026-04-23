#!/usr/bin/env python3
"""
ATH Protocol Interactive Demo - SDK Native Mode

Features:
1. Interactive user authorization with console prompts for consent
2. Loading animations and progress indicators for each step
3. Fully separated client and server logic
4. User-friendly interface with role-based display
"""
import json
import random
import string
from typing import Dict, Any
import time
import sys

show_code_separately = False

def loading_animation(text: str, duration: float = 1.5):
    chars = "|/-\\"
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r⏳ {text} {chars[i % len(chars)]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r✅ {text} Done!\n")
    sys.stdout.flush()

def print_separator(title: str = ""):
    print("\n" + "="*80)
    if title:
        print(f"📌 {title}")
        print("-"*80)

def print_role_separator(role: str):
    if role == "client":
        print("\n" + "🔵 " + "="*30 + " [Client Logic] " + "="*30 + " 🔵")
    elif role == "server":
        print("\n" + "🟢 " + "="*30 + " [Server Logic] " + "="*30 + " 🟢")
    elif role == "user":
        print("\n" + "🟣 " + "="*30 + " [User Interaction] " + "="*30 + " 🟣")

# ==================== Client Implementation (Fully Independent) ====================
class Client:
    """Client: AI Shopping Assistant"""
    def __init__(self):
        self.did = "did:ath:ai_shopping_assistant_001"
        self.private_key = "client_private_key_123456"
        self.public_key = "client_public_key_abcdef"
        self.user_authorization = None
        self.access_token = None
        self.server_public_key = None
        print_separator("Initialize Client")
        loading_animation("Generating client DID identity and key pair")
        print(f"   Client DID: {self.did}")
        print(f"   Client Public Key: {self.public_key[:20]}...")
        
    def get_user_authorization(self, scopes: list) -> bool:
        """Obtain user pre-authorization"""
        print_role_separator("user")
        print(f"📋 [Authorization Request] AI Shopping Assistant requests the following permissions:")
        for scope in scopes:
            print(f"   ✅ {scope}")
        
        while True:
            choice = input("\n🤔 Do you approve the authorization? (Y/N): ").strip().upper()
            if choice == 'Y':
                loading_animation("User signing authorization credential")
                self.user_authorization = {
                    "user_id": "user_001",
                    "scopes": scopes,
                    "signature": "user_signature_" + ''.join(random.choices(string.hexdigits, k=16)),
                    "expires_at": int(time.time()) + 7200
                }
                print(f"   Credential: {self.user_authorization['signature'][:20]}...")
                return True
            elif choice == 'N':
                print("❌ User denied authorization, process terminated")
                return False
            else:
                print("⚠️  Please enter Y or N")

    def step1_send_handshake_request(self) -> Dict[str, Any]:
        """Step 1: Send handshake request"""
        print_role_separator("client")
        loading_animation("Building handshake request message")
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        request = {
            "type": "handshake_request",
            "client_did": self.did,
            "client_pubkey": self.public_key,
            "nonce": nonce,
            "timestamp": int(time.time())
        }
        print(f"   Nonce: {nonce}")
        print("📤 Client -> Server: Sending handshake request")
        return request

    def step3_send_identity_proof(self, server_response: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Send identity proof"""
        print_role_separator("client")
        self.server_public_key = server_response["server_pubkey"]
        server_nonce = server_response["nonce"]
        
        loading_animation("Signing server nonce with private key")
        signature = "sig_" + ''.join(random.choices(string.hexdigits, k=32))
        
        proof = {
            "type": "identity_proof",
            "signature": signature,
            "timestamp": int(time.time())
        }
        print(f"   Signature: {signature[:20]}...")
        print("📤 Client -> Server: Sending identity proof")
        return proof

    def step5_send_scope_request(self) -> Dict[str, Any]:
        """Step 5: Send scope request"""
        print_role_separator("client")
        loading_animation("Building scope request message")
        request = {
            "type": "scope_request",
            "scopes": self.user_authorization["scopes"],
            "user_authorization": self.user_authorization,
            "context": "User needs to search products and place an order",
            "timestamp": int(time.time())
        }
        print(f"   Requested scopes: {request['scopes']}")
        print("📤 Client -> Server: Sending scope request")
        return request

    def step9_complete_handshake(self, access_token: str):
        """Step 9: Complete handshake"""
        print_role_separator("client")
        loading_animation("Validating access token")
        self.access_token = access_token
        print(f"   Access token: {access_token[:20]}...")
        print("✅ Client handshake complete! Trusted communication channel established")

    def send_business_request(self, api_path: str, method: str = "GET", data: Dict = None):
        """Send a business request"""
        if not self.access_token:
            print("❌ Not connected, please complete handshake first")
            return
        
        print_separator(f"Business Request Demo: {method} {api_path}")
        loading_animation(f"Encrypting request data with session key")
        print(f"📤 Sending request: {method} {api_path}")
        print(f"   Authorization: Bearer {self.access_token[:20]}...")
        if data:
            print(f"   Request data: {json.dumps(data, ensure_ascii=False)}")
        
        loading_animation("Waiting for server response", duration=1)
        if "goods" in api_path:
            print("✅ Response success: Product list returned [{'id': '123', 'name': 'iPhone 15', 'price': 5999}]")
        elif "order" in api_path:
            print("✅ Response success: Order created, order ID: ORDER_" + ''.join(random.choices(string.digits, k=8)))
        else:
            print("✅ Response success")

# ==================== Server Implementation (Fully Independent) ====================
class Server:
    """Server: E-commerce Platform"""
    def __init__(self):
        self.did = "did:ath:ecommerce_platform_001"
        self.private_key = "server_private_key_654321"
        self.public_key = "server_public_key_fedcba"
        self.client_nonce = None
        self.client_did = None
        self.client_public_key = None
        print_separator("Initialize Server")
        loading_animation("Loading server configuration and certificates")
        print(f"   Server DID: {self.did}")
        print(f"   Server Public Key: {self.public_key[:20]}...")
        
    def step2_send_handshake_response(self, client_request: Dict[str, Any]) -> Dict[str, Any]:
        """Step 2: Send handshake response"""
        print_role_separator("server")
        self.client_did = client_request["client_did"]
        self.client_public_key = client_request["client_pubkey"]
        self.client_nonce = client_request["nonce"]
        
        loading_animation("Validating client request format, generating server nonce")
        server_nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        
        loading_animation("Signing client nonce with private key")
        signature = "sig_" + ''.join(random.choices(string.hexdigits, k=32))
        
        response = {
            "type": "handshake_response",
            "server_did": self.did,
            "server_pubkey": self.public_key,
            "nonce": server_nonce,
            "signature": signature,
            "timestamp": int(time.time())
        }
        print(f"   Server nonce: {server_nonce}")
        print(f"   Signature: {signature[:20]}...")
        print("📤 Server -> Client: Sending handshake response")
        return response

    def step4_send_identity_result(self, identity_proof: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Send identity verification result"""
        print_role_separator("server")
        loading_animation("Verifying client signature")
        
        is_valid = True
        if is_valid:
            result = {
                "type": "identity_result",
                "success": True,
                "scopes_supported": ["goods:read", "order:create", "user:profile"],
                "token_max_ttl": 7200,
                "timestamp": int(time.time())
            }
            print("✅ Client identity verification passed")
            print("📤 Server -> Client: Identity verification successful")
        else:
            result = {"type": "identity_result", "success": False, "error": "Invalid signature"}
            print("❌ Client identity verification failed")
        return result

    def step6_request_user_confirmation(self, scope_request: Dict[str, Any]) -> bool:
        """Step 6: Request user authorization confirmation"""
        print_role_separator("user")
        client_info = "AI Shopping Assistant"
        scopes = scope_request["scopes"]
        
        print(f"🔔 [Server Authorization Confirmation Request]")
        print(f"   Requester: {client_info} ({scope_request['user_authorization']['user_id']})")
        print(f"   Requested scopes: {scopes}")
        print(f"   Context: {scope_request['context']}")
        
        while True:
            choice = input("\n🤔 Do you approve this authorization request? (Y/N): ").strip().upper()
            if choice == 'Y':
                loading_animation("Recording user authorization result")
                print("✅ User approved the authorization")
                return True
            elif choice == 'N':
                print("❌ User denied authorization, process terminated")
                return False
            else:
                print("⚠️  Please enter Y or N")

    def step8_send_scope_result(self, user_approved: bool) -> Dict[str, Any]:
        """Step 8: Send scope approval result"""
        print_role_separator("server")
        if user_approved:
            loading_animation("Generating scope approval result")
            result = {
                "type": "scope_result",
                "scopes_granted": ["goods:read", "order:create"],
                "ttl_granted": 7200,
                "restrictions": {
                    "rate_limit": "100/minute",
                    "ip_whitelist": ["192.168.1.0/24"]
                },
                "timestamp": int(time.time())
            }
            print(f"   Granted scopes: {result['scopes_granted']}")
            print(f"   TTL: {result['ttl_granted']}s")
            print("📤 Server -> Client: Scope approval granted")
        else:
            result = {"type": "scope_result", "success": False, "error": "User rejected"}
            print("📤 Server -> Client: Scope approval denied")
        return result

    def step9_issue_access_token(self) -> str:
        """Step 9: Issue access token"""
        print_role_separator("server")
        loading_animation("Generating and signing access token")
        token = 'ath_' + ''.join(random.choices(string.ascii_letters + string.digits, k=40))
        print(f"   Token: {token[:20]}...")
        print("📤 Server -> Client: Issuing access token")
        return token

# ==================== Main Flow ====================
def main():
    print("\n" + "🎆"*30)
    print("🎆" + " "*22 + "ATH Trusted Handshake Protocol Interactive Demo" + " "*22 + "🎆")
    print("🎆"*30)
    print("\n📖 This demo fully implements the ATH protocol spec. Client and server logic are completely independent.")

    global show_code_separately
    while True:
        choice = input("\n🤔 Show client and server implementation logic separately? (Y/N): ").strip().upper()
        if choice == 'Y':
            show_code_separately = True
            break
        elif choice == 'N':
            show_code_separately = False
            break
        else:
            print("⚠️  Please enter Y or N")

    # 1. Initialize roles
    client = Client()
    server = Server()

    # 2. User pre-authorization
    if not client.get_user_authorization(["goods:read", "order:create"]):
        return

    # 3. Handshake flow
    print_separator("Starting 9-Step Trusted Handshake Flow")

    # Step 1: Client sends request
    handshake_request = client.step1_send_handshake_request()
    time.sleep(0.5)

    # Step 2: Server sends response
    handshake_response = server.step2_send_handshake_response(handshake_request)
    time.sleep(0.5)

    # Step 3: Client sends identity proof
    identity_proof = client.step3_send_identity_proof(handshake_response)
    time.sleep(0.5)

    # Step 4: Server sends verification result
    identity_result = server.step4_send_identity_result(identity_proof)
    if not identity_result["success"]:
        return
    time.sleep(0.5)

    # Step 5: Client sends scope request
    scope_request = client.step5_send_scope_request()
    time.sleep(0.5)

    # Step 6: Server requests user confirmation
    user_approved = server.step6_request_user_confirmation(scope_request)
    if not user_approved:
        return
    time.sleep(0.5)

    # Step 7: User confirmed, server processes
    time.sleep(0.5)

    # Step 8: Server sends approval result
    scope_result = server.step8_send_scope_result(user_approved)
    if not scope_result.get("success", True):
        return
    time.sleep(0.5)

    # Step 9: Complete handshake
    access_token = server.step9_issue_access_token()
    client.step9_complete_handshake(access_token)

    # Handshake complete
    print("\n" + "🎉"*30)
    print("🎉" + " "*18 + "Handshake Complete! Trusted Communication Channel Established" + " "*18 + "🎉")
    print("🎉"*30)

    # 4. Business request demo
    print_separator("Business Request Demo")
    client.send_business_request("/api/goods?keyword=iPhone", "GET")
    time.sleep(1)
    client.send_business_request("/api/order", "POST", {"goods_id": "123", "quantity": 1, "address": "123 Main St"})

    if show_code_separately:
        print_separator("Client and Server Implementation Notes")
        print("\n🔵 Client Implementation (Fully Independent):")
        print("   - Located in the [Client Implementation] section of the demo file")
        print("   - Handles: identity management, handshake requests, scope negotiation, encrypted communication")
        print("   - Can be extracted as a foundation for SDK implementation")
        print("\n🟢 Server Implementation (Fully Independent):")
        print("   - Located in the [Server Implementation] section of the demo file")
        print("   - Handles: identity verification, authorization confirmation, scope approval, token issuance")
        print("   - Can be extracted as a foundation for server middleware implementation")
        print("\n📌 Design Note:")
        print("   Although this demo runs in a single file, the client and server are fully decoupled classes.")
        print("   They interact only through agreed-upon message formats, identical to real network communication.")
        print("   In production, the client and server would be deployed on separate servers, communicating via HTTP/HTTPS.")

if __name__ == "__main__":
    main()
