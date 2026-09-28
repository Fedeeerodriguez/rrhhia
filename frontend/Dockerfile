FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# La imagen de nginx sustituye las variables de estos templates al
# arrancar y los deja en /etc/nginx/conf.d/.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV API_UPSTREAM=http://backend:8000
# Solo se sustituye esa variable: sin el filtro, envsubst podria tocar
# las variables propias de nginx ($host, $scheme, $uri).
ENV NGINX_ENVSUBST_FILTER=API_UPSTREAM
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3     CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
