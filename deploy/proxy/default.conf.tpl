gzip on;

server {
  listen 8080;
  
  location /static {
    alias /vol/web;
  }
  
  location /docs {
    proxy_intercept_errors  on;
    proxy_redirect          off;
    proxy_hide_header       X-Amz-Id-2;
    proxy_hide_header       X-Amz-Request-Id;
    
    proxy_pass              "$PROXY_DOCS_URI";
  }
  
  location / {
    uwsgi_pass              "$SERVER_URI";
    
    proxy_set_header        Host "$host";
    proxy_set_header        X-Forwarded-For "$proxy_add_x_forwarded_for";
    uwsgi_pass_header       Token;
    
    client_max_body_size    32M;
    include                 /etc/nginx/uwsgi_params;
  }
}