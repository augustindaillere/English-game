# Stage 1: build the static site with Python
FROM python:3.12-alpine AS build
WORKDIR /src
COPY . .
RUN python3 build.py && python3 tests/check_site.py

# Stage 2: serve it with a tiny Nginx
FROM nginx:1.27-alpine
COPY docker/nginx-site.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
