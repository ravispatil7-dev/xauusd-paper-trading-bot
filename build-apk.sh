#!/bin/bash
# Build APK for XAU/USD Paper Trading Bot
# Requires: Node.js, Android SDK, Java JDK

echo "=========================================="
echo "  GoldBot APK Builder"
echo "=========================================="

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not found. Install from https://nodejs.org/"; exit 1; }
command -v java >/dev/null 2>&1 || { echo "❌ Java JDK not found. Install JDK 17+"; exit 1; }

# Install dependencies
echo "📦 Installing Capacitor..."
npm install

# Add Android platform
echo "🤖 Adding Android platform..."
npx cap add android 2>/dev/null || echo "Android platform already exists"

# Copy web assets
echo "📁 Copying web assets..."
npx cap copy android

# Update native dependencies
echo "🔄 Syncing native code..."
npx cap sync android

# Build APK
echo "🔨 Building APK..."
cd android
./gradlew assembleRelease

echo ""
echo "✅ APK built successfully!"
echo "📍 Location: android/app/build/outputs/apk/release/app-release-unsigned.apk"
echo ""
echo "To sign the APK for Play Store:"
echo "  keytool -genkey -v -keystore goldbot.keystore -alias goldbot -keyalg RSA -keysize 2048 -validity 10000"
echo "  jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore goldbot.keystore app-release-unsigned.apk goldbot"
echo "  zipalign -v 4 app-release-unsigned.apk GoldBot-v1.0.apk"
