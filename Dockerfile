FROM mingc/android-build-box:latest

WORKDIR /app

# Copy project files
COPY package.json package-lock.json* ./
COPY capacitor.config.json ./
COPY frontend/ ./frontend/
COPY backend/ ./backend/

# Install Node dependencies
RUN npm install
RUN npm install -g @capacitor/cli

# Add Android platform and build
RUN npx cap add android
RUN npx cap copy android
RUN npx cap sync android

# Build APK
WORKDIR /app/android
RUN ./gradlew assembleDebug

# Output APK path
RUN echo "APK built at: /app/android/app/build/outputs/apk/debug/app-debug.apk"

CMD ["cp", "/app/android/app/build/outputs/apk/debug/app-debug.apk", "/output/GoldBot.apk"]
