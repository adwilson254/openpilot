#!/usr/bin/env python3
import os

def inject_logo():
    spinner_path = "system/ui/spinner.py"
    if not os.path.exists(spinner_path):
        print(f"Error: {spinner_path} not found.")
        return

    with open(spinner_path, "r") as f:
        content = f.read()

    # Replace the logo texture string
    old_logo = 'gui_app.texture("images/ap_logo.png"'
    new_logo = 'gui_app.texture("images/openrivian_logo.png"'

    if old_logo in content:
        content = content.replace(old_logo, new_logo)
        with open(spinner_path, "w") as f:
            f.write(content)
        print("Successfully injected OpenRivian logo into spinner.py")
    elif new_logo in content:
        print("OpenRivian logo is already injected.")
    else:
        print("Warning: Could not find ap_logo.png string in spinner.py. Upstream may have changed.")

if __name__ == "__main__":
    print("Running OpenRivian Injection Script...")
    inject_logo()
