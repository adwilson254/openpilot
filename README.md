<div align="center">
  <img src="selfdrive/assets/images/openrivian_logo.png" width="200" alt="OpenRivian Logo" />

  <h1>OpenRivian</h1>
  <p>An open source driver assistance system tailored for Rivian vehicles.</p>
</div>

---

## 🌲 What is OpenRivian?
OpenRivian is a specialized fork of [sunnypilot](https://github.com/sunnyhaibin/sunnypilot) and [ap-dev](https://github.com/adventurepilotdev/ap-dev) (which are downstream of [openpilot](https://github.com/commaai/openpilot)). It is explicitly engineered and optimized for Rivian vehicle platforms. OpenRivian introduces custom CAN logic, dynamic UI modifications, and native compiling tailored for Rivian integration on Comma hardware.

## 🌿 Branch Architecture
OpenRivian relies on a heavily automated branching strategy to ensure flawless compatibility with upstream updates.

### 1. `clean` Branch
This is our **pristine mirror** branch. It tracks `adventurepilotdev/ap-dev` and syncs changes via a nightly GitHub Action. 
* **DO NOT** commit directly to this branch. 
* This branch serves as the foundation for our automated pipeline.

### 2. `dev` Branch
This is the **active deployment branch**. It contains all OpenRivian-specific logic, UI hooks, and custom assets.
* Nightly, a GitHub Action merges `clean` into `dev` and dynamically injects our OpenRivian modifications using python scripts.
* This is the branch you should use for active testing and development on your Comma device.

### 3. `pre` Branch (Prebuilt)
This is our **lean, release-ready branch**.
* Designed specifically for the Comma 4, this branch is compiled natively and stripped of all raw C/C++ source code to save massive amounts of space.
* It utilizes the `prebuilt` flag to ensure near-instant first boot times.
* *Note:* This branch is generated on-demand using the `selfdrive/ui/openrivian/scripts/build_prebuilt.sh` script.

## 🚀 Installation & Usage
To install OpenRivian on your Comma device:
1. Connect to Wi-Fi.
2. When prompted for custom software URL, enter: `adwilson254/dev`
3. Enjoy the drive.

### Building the Prebuilt Release (`pre`)
If you want to strip your local Comma codebase and create the fast-booting `pre` branch, simply SSH into your Comma and execute:
```bash
bash selfdrive/ui/openrivian/scripts/build_prebuilt.sh
```

---

## 📜 Licensing
OpenRivian inherits the [MIT License](LICENSE) and includes original work from comma.ai and sunnypilot. 

> **THIS IS ALPHA QUALITY SOFTWARE FOR RESEARCH PURPOSES ONLY. THIS IS NOT A PRODUCT. YOU ARE RESPONSIBLE FOR COMPLYING WITH LOCAL LAWS AND REGULATIONS. NO WARRANTY EXPRESSED OR IMPLIED.**
