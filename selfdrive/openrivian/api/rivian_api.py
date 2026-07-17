#!/usr/bin/env python3
import json
import requests
import uuid
from openpilot.common.params import Params

RIVIAN_GRAPHQL_URL = "https://rivian.com/api/gql/gateway/graphql"

# (connect, read) seconds. Every request MUST carry a timeout: the mici settings
# panel calls this client synchronously from the UI thread, and requests' default
# is to wait forever -- an LTE dead zone would otherwise hang the in-car UI.
REQUEST_TIMEOUT = (5, 15)

class RivianAPI:
    def __init__(self):
        self.params = Params()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "OpenRivian/1.0",
            "Apollographql-Client-Name": "com.rivian.android.consumer",
            "Apollographql-Client-Version": "2.10.0"
        })
        self._load_tokens()

    def _load_tokens(self):
        acc = self.params.get("RivianAccessToken")
        if acc:
            acc_str = acc.decode("utf-8") if isinstance(acc, bytes) else str(acc)
            try:
                tokens = json.loads(acc_str)
                self.access_token = tokens.get("accessToken")
                self.refresh_token = tokens.get("refreshToken")
                self.user_session_token = tokens.get("userSessionToken")
            except json.JSONDecodeError:
                # Fallback for old tokens
                self.access_token = acc_str
                ref = self.params.get("RivianRefreshToken")
                self.refresh_token = (ref.decode("utf-8") if isinstance(ref, bytes) else str(ref)) if ref else None
                self.user_session_token = None
        else:
            self.access_token = None
            self.refresh_token = None
            self.user_session_token = None
            
        if self.user_session_token:
            self.session.headers.update({"u-sess": self.user_session_token})
        elif self.access_token:
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})

    def _save_tokens(self, access_token, refresh_token, user_session_token):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_session_token = user_session_token
        
        tokens_json = json.dumps({
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "userSessionToken": user_session_token
        })
        self.params.put("RivianAccessToken", tokens_json)
        
        if self.user_session_token:
            self.session.headers.update({"u-sess": self.user_session_token})

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

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload, timeout=REQUEST_TIMEOUT)
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

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload, timeout=REQUEST_TIMEOUT)
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
            self._save_tokens(result["accessToken"], result["refreshToken"], result["userSessionToken"])
            return {"status": "success"}
        elif result.get("__typename") == "MobileMFALoginResponse":
            self.otp_token = result["otpToken"]
            self.email = email
            return {"status": "mfa_required"}
        else:
            raise Exception(f"Login failed: {result}")

    def login_with_otp(self, otp_code):
        if not hasattr(self, "otp_token"):
            raise Exception("No active MFA session. Call login() first.")

        query = """
        mutation LoginWithOTP($email: String!, $otpCode: String!, $otpToken: String!) {
            loginWithOTPV2(email: $email, otpCode: $otpCode, otpToken: $otpToken) {
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
            "variables": {"email": self.email, "otpCode": otp_code, "otpToken": self.otp_token}
        }

        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload, timeout=REQUEST_TIMEOUT)
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
            
        result = result.get("loginWithOTPV2", {})
        
        if result.get("__typename") == "MobileLoginResponse":
            self._save_tokens(result["accessToken"], result["refreshToken"], result["userSessionToken"])
            return {"status": "success"}
        else:
            raise Exception(f"MFA Login failed: {result}")

    def is_authenticated(self):
        return self.access_token is not None

    # -- vehicle state (energy) ------------------------------------------------
    # Query shapes follow the community-documented Rivian mobile GraphQL API
    # (rivian-python-api / rivian-apidocs). Rivian's API is unofficial and can
    # change; every accessor below is defensive: any unexpected shape returns
    # None/[] instead of raising, and callers treat that as "data unavailable".
    # Timestamped fields arrive as objects like {"value": 71.5, ...}; _ts_value
    # accepts both that shape and a raw scalar.

    @staticmethod
    def _ts_value(field):
        if isinstance(field, dict):
            return field.get("value")
        return field

    def _graphql(self, operation, query, variables):
        payload = {"operationName": operation, "query": query, "variables": variables}
        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
        return data.get("data") or {}

    def get_vehicles(self):
        """Return [{'id': ..., 'name': ...}, ...] for the account, or [] on any failure."""
        if not self.is_authenticated():
            return []
        query = """
        query GetUserVehicles {
            currentUser {
                __typename
                vehicles {
                    id
                    name
                    vin
                }
            }
        }
        """
        try:
            data = self._graphql("GetUserVehicles", query, {})
            vehicles = (data.get("currentUser") or {}).get("vehicles") or []
            return [v for v in vehicles if isinstance(v, dict) and v.get("id")]
        except Exception:
            return []

    def get_vehicle_state(self, vehicle_id):
        """Return {'soc_percent', 'range_miles', 'charger_state'} (values may be None),
        or None when the query fails or the account/vehicle is unavailable."""
        if not self.is_authenticated() or not vehicle_id:
            return None
        query = """
        query GetVehicleState($vehicleID: String!) {
            vehicleState(id: $vehicleID) {
                __typename
                batteryLevel { value }
                distanceToEmpty { value }
                chargerState { value }
            }
        }
        """
        try:
            data = self._graphql("GetVehicleState", query, {"vehicleID": vehicle_id})
            vs = data.get("vehicleState")
            if not isinstance(vs, dict):
                return None
            soc = self._ts_value(vs.get("batteryLevel"))
            dte = self._ts_value(vs.get("distanceToEmpty"))  # kilometers per community docs
            charger = self._ts_value(vs.get("chargerState"))
            return {
                "soc_percent": float(soc) if soc is not None else None,
                "range_miles": round(float(dte) * 0.621371, 1) if dte is not None else None,
                "charger_state": str(charger) if charger is not None else None,
            }
        except Exception:
            return None

    def get_user_info(self):
        if not self.create_csrf_token():
            raise Exception("Failed to acquire CSRF token for user info request")
            
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
        resp = self.session.post(RIVIAN_GRAPHQL_URL, json=payload, timeout=REQUEST_TIMEOUT)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error {resp.status_code}: {resp.text}") from e
        data = resp.json()
        if "errors" in data:
            raise Exception(f"GraphQL Error: {data['errors']}")
        return data
