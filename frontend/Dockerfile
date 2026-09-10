FROM nginx:1.27-alpine

ARG API_URL=http://localhost:8000

COPY frontend/index.html frontend/app.js frontend/styles.css frontend/config.js /usr/share/nginx/html/
RUN printf 'window.FAIRSEAT_API_URL = "%s";\n' "$API_URL" > /usr/share/nginx/html/config.js

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80