gzip on;

upstream app_upstream {
  server "$SERVER_URI";
  server "$SERVER_REPLICA_URI";
}

server {
  listen 8080;
  
  resolver 127.0.0.11 valid=5s;
  
  # Pass media files directly to S3
  location ~ ^/files/media/(.*)$ {
    proxy_intercept_errors  on;
    proxy_redirect          off;
    proxy_hide_header       X-Amz-Id-2;
    proxy_hide_header       X-Amz-Request-Id;
    
    proxy_pass "https://$S3_STORAGE_BUCKET_NAME.s3.amazonaws.com/$1";
  }
  
  # Pass static files to mounted volume
  location ~ ^/files/static/(.*)$ {
    alias "/vol/web/static/$1";
  }
  
  # Docs go to S3 bucket the files were uploaded to
  location /docs {
    proxy_intercept_errors  on;
    proxy_redirect          off;
    proxy_hide_header       X-Amz-Id-2;
    proxy_hide_header       X-Amz-Request-Id;
    
    proxy_pass              "$PROXY_DOCS_URI";
  }
  
  # Pass everything else to Django
  location / {
    proxy_pass                 http://app_upstream;
    
    proxy_set_header           Host "$host";
    proxy_set_header           X-Forwarded-For "$proxy_add_x_forwarded_for";
    proxy_pass_header          Token;
    
    client_max_body_size       32M;
    include                    /etc/nginx/uwsgi_params;
    proxy_send_timeout         120s;
    proxy_read_timeout         300s;
    proxy_connect_timeout      60s;
    
    proxy_buffer_size          128k;
    proxy_buffers              4 256k;
    proxy_busy_buffers_size    256k;
  }
}