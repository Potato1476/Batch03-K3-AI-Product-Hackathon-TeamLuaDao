FROM node:22-alpine AS build

WORKDIR /app
COPY codebase/apps/web/package.json codebase/apps/web/package-lock.json ./
RUN npm ci
COPY codebase/apps/web/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY codebase/apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
