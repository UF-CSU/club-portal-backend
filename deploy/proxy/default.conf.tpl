server {
  listen 8080;
  # resolver "$DNS_RESOLVER" valid=5s;
  
  location /static {
    alias /vol/web;
  }
  
  location / {
    uwsgi_pass "$SERVER_URI";
    
    proxy_set_header        Host "$host";
    proxy_set_header        X-Forwarded-For "$proxy_add_x_forwarded_for";
    uwsgi_pass_header       Token;
    
    client_max_body_size    32M;
    include /etc/nginx/uwsgi_params;
  }
}