# DEPLOYMENT - DocGen API Fase 1

## 1. Deployment Local (Desenvolvimento)

### 1.1 Setup Manual

```bash
# Clone ou navegue até o diretório
cd c:\www\DocGen3\ PP

# Criar virtual environment (opcional mas recomendado)
python -m venv venv

# Ativar venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python main.py

# Servidor rodando em http://localhost:8000
```

### 1.2 Com Docker Compose

```bash
# Build e executa container
docker-compose up --build

# Em background
docker-compose up -d

# Ver logs
docker-compose logs -f api

# Parar
docker-compose down
```

---

## 2. Deployment Staging/Production

### 2.1 Linux (Ubuntu/Debian com Nginx + Gunicorn)

```bash
# 1. SSH no servidor
ssh user@your-server.com

# 2. Clone repo
git clone https://github.com/docgen/api.git /opt/docgen
cd /opt/docgen

# 3. Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Environment variables
cp .env.example .env
nano .env  # Editar com valores reais

# 5. Gunicorn service
sudo tee /etc/systemd/system/docgen.service << EOF
[Unit]
Description=DocGen API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/docgen
Environment="PATH=/opt/docgen/venv/bin"
ExecStart=/opt/docgen/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --timeout 120 \
  --access-logfile /var/log/docgen/access.log \
  --error-logfile /var/log/docgen/error.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable docgen
sudo systemctl start docgen
systemctl status docgen

# 6. Nginx proxy
sudo tee /etc/nginx/sites-available/docgen << EOF
upstream docgen_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.docgen.com;

    location / {
        proxy_pass http://docgen_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeout para PDF generation
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # SSL - Usar certbot
    # certbot --nginx -d api.docgen.com
}
EOF

sudo ln -s /etc/nginx/sites-available/docgen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2.2 Heroku (Alternativamente simples)

```bash
# 1. Criar arquivo Procfile
echo "web: gunicorn main:app --worker-class uvicorn.workers.UvicornWorker" > Procfile

# 2. Deploy
heroku create docgen-api
git push heroku main

# 3. Logs
heroku logs --tail
```

### 2.3 AWS (ECS + Fargate com Docker)

```bash
# 1. Build e push para ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t docgen-api:1.0.0 .
docker tag docgen-api:1.0.0 YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docgen-api:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/docgen-api:latest

# 2. Criar ECS Task Definition (veja task-definition.json)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 3. Criar ECS Service
aws ecs create-service --cluster docgen-prod \
  --service-name docgen-api \
  --task-definition docgen-api:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

---

## 3. Variáveis de Ambiente (production)

```bash
# .env (production)
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://app.docgen.com"]
MAX_PAYLOAD_SIZE=1048576
ENVIRONMENT=production
DEBUG=False

# Futuras fases
# JWT_SECRET=<strong-secret-key>
# DB_HOST=prod-db.aws.rds.amazonaws.com
# DB_USER=docgen_user
# DB_PASSWORD=<secure-password>
# DB_NAME=docgen_prod
```

---

## 4. Monitoramento & Logs

### 4.1 Gunicorn Logs
```bash
tail -f /var/log/docgen/access.log
tail -f /var/log/docgen/error.log
```

### 4.2 Systemd Logs
```bash
journalctl -u docgen -f
```

### 4.3 Docker Logs
```bash
docker-compose logs -f api
docker logs docgen_api -f
```

### 4.4 Health Check
```bash
curl http://api.docgen.com/health
```

---

## 5. Escalabilidade (Horizontal)

### 5.1 Load Balancer (Nginx)
```nginx
upstream docgen_cluster {
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}

server {
    listen 80;
    server_name api.docgen.com;

    location / {
        proxy_pass http://docgen_cluster;
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }
}
```

### 5.2 Kubernetes (K8s)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docgen-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: docgen-api
  template:
    metadata:
      labels:
        app: docgen-api
    spec:
      containers:
      - name: api
        image: YOUR_REGISTRY/docgen-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

---

## 6. Backup & Disaster Recovery (Fase 2+)

- Backups automáticos do PostgreSQL
- Replicação para múltiplas regiões
- RTO (Recovery Time Objective): 1 hora
- RPO (Recovery Point Objective): 15 minutos

---

## 7. Checklist de Deploy

- [ ] Instalar todas as dependências (requirements.txt)
- [ ] Configurar variáveis de ambiente (.env)
- [ ] Executar testes (`pytest test_main.py`)
- [ ] Build Docker (`docker build -t docgen-api:VERSION .`)
- [ ] Push para registry (AWS ECR, Docker Hub, etc)
- [ ] Deploy em staging para teste
- [ ] SSL/TLS configurado (HTTPS)
- [ ] CORS configurado para domínios corretos
- [ ] Health check respondendo
- [ ] Logs sendo coletados
- [ ] Monitoramento ativo (APM, alertas)
- [ ] Roadmap Fase 2+ documentado

---

Próxima fase: Persistência com PostgreSQL + JWT Authentication
