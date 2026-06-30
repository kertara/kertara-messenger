
# Build Instructions

This document provides a guide for building the **Kertara Messenger** application from source code into an executable (`.exe`) file for Windows.

## Prerequisites
Before you begin, ensure you have the following installed:
* **Python 3.10+**
* **Git**
* **Pip** (Python package manager)

## Build Steps

### 1. Prepare the Environment
Clone the repository and navigate to the project directory:
```bash
git clone [https://github.com/kertara/kertara-messenger.git](https://github.com/kertara/kertara-messenger.git)
cd kertara-messenger

```

### 2. Install Dependencies

Install all required libraries:

```bash
pip install -r requirements.txt
pip install cython pyinstaller

```

### 3. Compile Extensions (Cython)

To improve performance and protect your code logic, use Cython to convert your `.py` files into binary modules:

```bash
python setup.py build_ext --inplace

```

### 4. Build the Executable (PyInstaller)

Use PyInstaller to bundle the application into a single executable file (`.exe`):

```bash
py -m PyInstaller --onefile --windowed ^
--add-data "assets;assets" ^
--hidden-import=argon2 ^
--hidden-import=cffi ^
--hidden-import=cryptography ^
--hidden-import=charset_normalizer ^
--collect-all=stem ^
--icon=assets/icon.ico ^
--name=kertara-messenger-v0.1.0-alpha ^
run.py

```

### 5. Build Output

Once the process is complete, your executable file (`.exe`) will be located in the `/dist` folder.

## Important Notes

* **Tor Expert Bundle:** The Tor binary folder is not included in the automatic PyInstaller build process to keep the file size minimal. You must manually download and place the Tor folder in the application directory after the build is complete.
* **Versioning:** Ensure the output filename matches the current release version.
* **Environment:** It is highly recommended to use a Virtual Environment (`venv`) to keep your dependencies organized.


*© 2026 Kertara.*
