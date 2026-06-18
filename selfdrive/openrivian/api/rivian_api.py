#!/usr/bin/env python3
import json
import requests
import uuid
from openpilot.common.params import Params

RIVIAN_GRAPHQL_URL = "https://rivian.com/api/gql/gateway/graphql"

class RivianAPI:
    def __init__(self):
        self.params = Params()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "OpenRivian/1.0",
            "Apollographql-Client-Name": "com.rivian.ios.consumer",
            "Apollographql-Client-Version": "2.10.0"
        })
        self._load_tokens()

    def _load_tokens(self):
        acc = self.params.get("RivianAccessToken")
        ref = self.params.get("RivianRefreshToken")
        self.access_token = acc.decode("utf-8") if acc else None
        self.refresh_token = ref.decode("utf-8") if ref else None
        if self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def _save_tokens(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.params.put("RivianAccessToken", access_token)
        self.params.put("RivianRefreshToken", refresh_token)
        self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def create_csrf_token(self):
        query = """
        mutation CreateCSRFToken {
            createCsrfToken {
                __typename
                csrfToken
                appSessionToken
            }
        }
        """
        payload = {
            "operationName": "CreateCSRFToken",
            "query": query,
            "variables": {}
        }
        
        # We need a random device ID
        device_id = str(uuid.uuid4())
        self.session.headers.update({
            "v-cmd": "1",
            "dc-id": device_id
        })

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error {resp.status_code}: {resp.text}") from e
        data = resp.json()
        
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
            
        result = data.get("data")
        if not result:
            return False
            
        result = result.get("createCsrfToken", {})
        if "csrfToken" in result:
            csrf = result["csrfToken"]
            app_session = result["appSessionToken"]
            self.session.headers.update({
                "csrf-token": csrf,
                "a-sess": app_session
            })
            return True
        return False

    def login(self, email, password):
        if not self.create_csrf_token():
            raise Exception("Failed to acquire CSRF token")

        query = """
        mutation Login($email: String!, $password: String!) {
            login(email: $email, password: $password) {
                __typename
                ... on MobileLoginResponse {
                    accessToken
                    refreshToken
                    userSessionToken
                }
                ... on MobileMFALoginResponse {
                    otpToken
                }
            }
        }
        """
        payload = {
            "operationName": "Login",
            "query": query,
            "variables": {"email": email, "password": password}
        }

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error {resp.status_code}: {resp.text}") from e
        data = resp.json()

        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
            
        result = data.get("data")
        if not result:
            raise Exception("GraphQL response contained no data.")
            
        result = result.get("login", {})
        
        if result.get("__typename") == "MobileLoginResponse":
            self._save_tokens(result["accessToken"], result["refreshToken"])
            return {"status": "success"}
        elif result.get("__typename") == "MobileMFALoginResponse":
            self.otp_token = result["otpToken"]
            return {"status": "mfa_required"}
        else:
            raise Exception(f"Login failed: {result}")

    def login_with_otp(self, otp_code):
        if not hasattr(self, "otp_token"):
            raise Exception("No active MFA session. Call login() first.")

        query = """
        mutation LoginWithOTP($otpCode: String!, $otpToken: String!) {
            loginWithOtp(otpCode: $otpCode, otpToken: $otpToken) {
                __typename
                ... on MobileLoginResponse {
                    accessToken
                    refreshToken
                    userSessionToken
                }
            }
        }
        """
        payload = {
            "operationName": "LoginWithOTP",
            "query": query,
            "variables": {"otpCode": otp_code, "otpToken": self.otp_token}
        }

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error {resp.status_code}: {resp.text}") from e
        data = resp.json()

        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
            
        result = data.get("data")
        if not result:
            raise Exception("GraphQL response contained no data.")
            
        result = result.get("loginWithOtp", {})
        
        if result.get("__typename") == "MobileLoginResponse":
            self._save_tokens(result["accessToken"], result["refreshToken"])
            return {"status": "success"}
        else:
            raise Exception(f"MFA Login failed: {result}")

    def is_authenticated(self):
        return self.access_token is not None

    def get_user_info(self):
        query = """
        query GetUser {
            currentUser {
                __typename
                ... on User {
                    firstName
                    lastName
                    email
                }
            }
        }
        """
        payload = {"operationName": "GetUser", "query": query, "variables": {}}
        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error {resp.status_code}: {resp.text}") from e
        data = resp.json()
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
        return data
