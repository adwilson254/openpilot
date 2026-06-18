#!/usr/bin/env python3
import sys
import getpass

# Add openpilot root to python path so we can import selfdrive
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from selfdrive.openrivian.api.rivian_api import RivianAPI

def main():
    print("======================================")
    print("   OpenRivian Auth CLI (Fallback)")
    print("======================================")
    
    api = RivianAPI()
    
    if api.is_authenticated():
        print("[!] It looks like you are already authenticated!")
        print("[!] To force re-authentication, we will override existing tokens.")
    
    email = input("Rivian Email: ")
    password = getpass.getpass("Rivian Password: ")
    
    print("\n[*] Sending Login Request...")
    try:
        res = api.login(email, password)
        
        if res["status"] == "mfa_required":
            print("\n[!] MFA Required! A 6-digit code has been sent to your phone.")
            otp_code = input("Enter 6-digit code: ")
            print("[*] Verifying code...")
            mfa_res = api.login_with_otp(otp_code)
            if mfa_res["status"] == "success":
                print("\n[+] SUCCESS! Access tokens acquired and saved to Params.")
        elif res["status"] == "success":
            print("\n[+] SUCCESS! Access tokens acquired and saved to Params (No MFA needed).")
            
        # Verify
        print("[*] Fetching user info to verify...")
        user_info = api.get_user_info()
        print(f"[+] Authenticated as: {user_info}")
            
    except Exception as e:
        print(f"\n[-] Authentication Failed: {e}")

if __name__ == "__main__":
    main()
