FROM nginxinc/nginx-unprivileged:1-alpine
LABEL maintainer="web@ikehunter.dev"

COPY ./default.conf.tpl /etc/nginx/default.conf.tpl
COPY ./includes /etc/nginx/includes
COPY ./entrypoint.sh /entrypoint.sh

USER root

RUN apk add --no-cache --upgrade bash && \
    mkdir -p /vol/web && \
    chmod 755 /vol/web && \
    chown nginx:nginx /vol/web && \
    touch /etc/nginx/conf.d/default.conf && \
    chown nginx:nginx /etc/nginx/conf.d/default.conf && \
    chmod +x /entrypoint.sh

USER nginx

EXPOSE 8080
VOLUME /vol/web

CMD ["/entrypoint.sh"]