# Building APK for XAU/USD Paper Trading Bot

## Method 1: PWA Install (Easiest - No Build Required)
The app is already a Progressive Web App (PWA). Users can install it directly:

### Android Chrome:
1. Open the app URL in Chrome
2. Tap the menu (⋮) → "Add to Home screen"
3. The app installs like a native app with its own icon

### iOS Safari:
1. Open the app URL in Safari
2. Tap Share → "Add to Home Screen"
3. The app appears on your home screen

**Features of PWA install:**
- Works offline (cached assets)
- Full-screen app experience (no browser UI)
- Push notifications for trading signals
- Automatic updates when server updates
- No app store approval needed

---

## Method 2: Native APK Build (Using Capacitor)

### Prerequisites
1. **Node.js** (v18+) - https://nodejs.org/
2. **Android Studio** - https://developer.android.com/studio
3. **Java JDK 17** - https://adoptium.net/
4. **Android SDK** (installed via Android Studio)

### Step-by-Step Build

#### Step 1: Install Node Dependencies
```bash
cd xauusd-paper-trading-bot
npm install
```

#### Step 2: Add Android Platform
```bash
npx cap add android
```

#### Step 3: Copy Web Assets
```bash
npx cap copy android
npx cap sync android
```

#### Step 4: Open in Android Studio
```bash
npx cap open android
```

#### Step 5: Build APK in Android Studio
1. In Android Studio, wait for Gradle sync to complete
2. Go to **Build → Build Bundle(s) / APK(s) → Build APK(s)**
3. Or use: **Build → Generate Signed Bundle / APK** for release

#### Step 6: Find Your APK
- Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release APK: `android/app/build/outputs/apk/release/app-release-unsigned.apk`

### Automated Build (Using Script)
```bash
# Make script executable
chmod +x build-apk.sh

# Run build
./build-apk.sh
```

### Signing the APK for Distribution
```bash
# Generate keystore (do this once)
keytool -genkey -v   -keystore goldbot.keystore   -alias goldbot   -keyalg RSA   -keysize 2048   -validity 10000

# Sign the APK
jarsigner -verbose   -sigalg SHA1withRSA   -digestalg SHA1   -keystore goldbot.keystore   app-release-unsigned.apk   goldbot

# Optimize APK
zipalign -v 4 app-release-unsigned.apk GoldBot-v1.0.apk
```

---

## Method 3: Online Build Services (No Local Setup)

### Option A: Ionic Appflow
1. Push code to GitHub
2. Connect repo to Ionic Appflow
3. Build APK in cloud

### Option B: GitHub Actions
Create `.github/workflows/build-apk.yml`:
```yaml
name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm install
      - run: npm install -g @capacitor/cli
      - run: npx cap add android
      - run: npx cap copy android
      - uses: android-actions/setup-android@v2
      - run: cd android && ./gradlew assembleDebug
      - uses: actions/upload-artifact@v3
        with:
          name: apk
          path: android/app/build/outputs/apk/debug/
```

### Option C: Docker Build
```bash
# Use pre-configured Android build container
docker run -v $(pwd):/project   mingc/android-build-box   bash -c "cd /project && ./build-apk.sh"
```

---

## APK Features

| Feature | PWA | Native APK |
|---------|-----|------------|
| Install from browser | ✅ | ❌ |
| Install from APK file | ❌ | ✅ |
| Offline trading | ✅ (cached) | ✅ |
| Push notifications | ✅ | ✅ |
| Background sync | ✅ | ✅ |
| Native performance | Good | Best |
| App store distribution | ❌ | ✅ (Play Store) |
| Auto-updates | ✅ | Via Play Store |
| File size | ~50KB | ~15MB |

---

## Recommended Approach

**For personal use:** Use PWA install (Method 1) - instant, no build needed
**For distribution:** Use Capacitor build (Method 2) - professional APK for Play Store

## Troubleshooting

### "Gradle sync failed"
- Update Android Studio to latest version
- Check `File → Settings → Build → Gradle` settings

### "Java version mismatch"
- Set JAVA_HOME to JDK 17: `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk`

### "SDK not found"
- Set ANDROID_SDK_ROOT in `local.properties`
- Or use Android Studio's SDK Manager

### Build takes too long
- First build downloads dependencies (~10 min)
- Subsequent builds are faster (~1-2 min)
