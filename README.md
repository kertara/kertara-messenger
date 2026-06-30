---

# Kertara Messenger

Kertara Messenger is a privacy-focused communication platform that prioritizes user data security through end-to-end encryption and anonymous routing via the Tor network.

This project is now **Open Source**, promoting transparency and community collaboration.

## Key Features

* **End-to-End Encryption:** All messages are encrypted directly on your device; only you and the recipient can read them.
* **Maximum Privacy:** Integrated with the Tor network to keep your identity and physical location hidden from surveillance.
* **Local Data Storage:** Your contact list and security keys are stored locally on your device. Your privacy is our priority.
* **Full Control:** You retain complete control over your identity and contact list without any third-party interference.

## Installation & Development

### For Users

1. Download the latest release from the [Releases page](https://github.com/kertara/kertara-messenger/releases).
2. Extract the files to a folder on your computer.
3. **Important:** Download the required Tor Expert Bundle based on your system architecture and extract it into the project folder:
* [Tor Expert Bundle (x86_64)](https://archive.torproject.org/tor-package-archive/torbrowser/15.0.17/tor-expert-bundle-windows-x86_64-15.0.17.tar.gz)
* [Tor Expert Bundle (i686)](https://archive.torproject.org/tor-package-archive/torbrowser/15.0.17/tor-expert-bundle-windows-i686-15.0.17.tar.gz)


4. Run `kertara-messenger-v0.1.0-alpha.exe`.
5. Wait for the Tor network initialization to reach 100%.

### For Developers (Contributors)

To run the application from the source code:

1. Clone this repository:

```bash
git clone https://github.com/kertara/kertara-messenger.git

```

2. Download the appropriate Tor Expert Bundle from the links provided in the User section above and extract it into the cloned directory.
3. Install the required dependencies:

```bash
pip install -r requirements.txt

```

4. Run the application:

```bash
python main.py

```

## Project Status (Alpha)

This application is currently in the **Alpha** testing phase. Bugs and technical issues may occur. We highly appreciate your feedback and encourage you to report any bugs or suggest features via the [GitHub Issue Tracker](https://github.com/kertara/kertara-messenger/issues).

## License

This project is open-source and licensed under the **MIT License**.
*You are permitted to use, modify, and distribute this code in accordance with the terms specified in the [LICENSE](https://raw.githubusercontent.com/kertara/kertara-messenger/refs/heads/main/LICENSE) file.*

---

© 2026 Kertara.