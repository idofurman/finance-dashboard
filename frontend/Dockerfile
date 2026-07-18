FROM nginx:1.27-alpine
COPY login.html index.html /usr/share/nginx/html/
COPY style.css favicon.ico favicon-16x16.png favicon-32x32.png \
     android-chrome-192x192.png android-chrome-512x512.png \
     apple-touch-icon.png site.webmanifest \
     /usr/share/nginx/html/frontend/
COPY nginx.conf /etc/nginx/conf.d/default.conf
