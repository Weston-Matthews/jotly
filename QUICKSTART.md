# Quick Start Guide

## Getting Started in 5 Minutes

### Step 1: Install Python & Dependencies
```bash
# Make sure you have Python 3.7+ installed
python --version

# Navigate to the project folder
cd noteapp

# Install Kivy
pip install -r requirements.txt
```

### Step 2: Test on Desktop
```bash
# Run the app
python main.py
```

You should see the app window open with the main screen!

### Step 3: Try It Out
1. Click "+ Note" to create a note
2. Type a title and some content
3. Select text and click **B** for bold, **I** for italic
4. Click "← Back" to return (auto-saves)
5. Try the search feature!

### Step 4: Build for Android (Optional)

**First time setup:**
```bash
# Install buildozer
pip install buildozer cython

# Install Android build dependencies (Ubuntu/Debian)
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# For other systems, see: https://buildozer.readthedocs.io/en/latest/installation.html
```

**Build the APK:**
```bash
# Build debug APK (first build takes 20-30 minutes)
buildozer android debug

# The APK will be in: bin/noteapp-0.1-arm64-v8a-debug.apk
```

**Install on your Android device:**
```bash
# Connect your phone via USB with USB debugging enabled
# Install the APK
adb install bin/noteapp-0.1-arm64-v8a-debug.apk
```

## Common Issues

### "Kivy not found"
```bash
pip install --upgrade pip
pip install kivy==2.3.0
```

### "Permission denied" on Android
Make sure you've enabled the storage permissions in buildozer.spec:
```
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
```

### App crashes on Android
- Check logcat: `adb logcat | grep python`
- Rebuild with: `buildozer android clean` then `buildozer android debug`

## What's Next?

Check out **README.md** for:
- Detailed architecture explanation
- Feature ideas to implement
- Performance optimization tips
- Troubleshooting guide

## Quick Code Tour

- `main.py` - App startup
- `database/db_manager.py` - All database logic
- `models/` - Business logic for notes, tasks, folders
- `ui/screens/` - The three main screens
- `ui/widgets/rich_text_editor.py` - The formatting toolbar

Happy coding! 🚀