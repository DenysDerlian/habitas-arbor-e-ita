# Instruções para Deploy - Habitas Arbor-e-ita

Este documento contém as instruções completas para fazer o deploy da aplicação Django.

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Banco de dados configurado (PostgreSQL recomendado para produção)
- Servidor web (Nginx + Gunicorn recomendado)

## 📦 Arquivos Necessários para Deploy

Os seguintes arquivos devem ser enviados para o servidor:

```
habitas/
├── habitas/              # Configurações do projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── main/                 # Aplicação principal
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── migrations/      # ⚠️ IMPORTANTE: Incluir todas as migrações
│   ├── templates/
│   └── static/
├── manage.py
├── requirements.txt      # Dependências do projeto
└── staticfiles/          # Arquivos estáticos coletados (será gerado)

Arquivos na raiz:
├── requirements.txt
├── INSTRUCOES_DEPLOY.md (este arquivo)
└── README.md (se existir)
```

## 🚀 Passos para Deploy

### 1. Preparar o Ambiente no Servidor

```bash
# Criar ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

⚠️ **IMPORTANTE**: Antes de fazer o deploy, configure as seguintes variáveis no `settings.py`:

```python
# Em habitas/settings.py, alterar:

DEBUG = False  # ⚠️ MUDAR PARA False EM PRODUÇÃO

ALLOWED_HOSTS = ['seu-dominio.com', 'www.seu-dominio.com', 'IP_DO_SERVIDOR']

# Configurar STATIC_ROOT para coletar arquivos estáticos
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configurar banco de dados de produção
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # ou outro banco
        'NAME': 'nome_do_banco',
        'USER': 'usuario_banco',
        'PASSWORD': 'senha_banco',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Configurar SECRET_KEY (gerar uma nova para produção)
# Use: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = 'sua-secret-key-gerada-aqui'
```

### 3. Executar Migrações do Banco de Dados

```bash
# Aplicar todas as migrações (incluindo as novas)
python manage.py migrate

# Se necessário, criar superusuário
python manage.py createsuperuser
```

### 4. Coletar Arquivos Estáticos

```bash
# Coletar todos os arquivos estáticos (CSS, JS, imagens)
python manage.py collectstatic --noinput
```

Este comando criará a pasta `staticfiles/` com todos os arquivos estáticos.

### 5. Configurar Servidor Web (Nginx + Gunicorn)

#### Instalar Gunicorn

```bash
pip install gunicorn
```

#### Criar arquivo de configuração do Gunicorn

Criar arquivo `gunicorn_config.py`:

```python
bind = "127.0.0.1:8000"
workers = 3
timeout = 120
```

#### Configurar Nginx

Exemplo de configuração `/etc/nginx/sites-available/habitas`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;

    location /static/ {
        alias /caminho/para/projeto/staticfiles/;
    }

    location /media/ {
        alias /caminho/para/projeto/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 6. Iniciar o Servidor

#### Opção 1: Gunicorn diretamente (para testes)

```bash
gunicorn habitas.wsgi:application --config gunicorn_config.py
```

#### Opção 2: Usando systemd (recomendado para produção)

Criar arquivo `/etc/systemd/system/habitas.service`:

```ini
[Unit]
Description=Habitas Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/caminho/para/projeto/habitas
ExecStart=/caminho/para/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/caminho/para/projeto/habitas/habitas.sock \
          habitas.wsgi:application

[Install]
WantedBy=multi-user.target
```

Iniciar serviço:

```bash
sudo systemctl start habitas
sudo systemctl enable habitas
```

## ✅ Checklist de Deploy

- [ ] Python 3.8+ instalado
- [ ] Ambiente virtual criado e ativado
- [ ] `requirements.txt` instalado
- [ ] `DEBUG = False` no settings.py
- [ ] `ALLOWED_HOSTS` configurado
- [ ] `SECRET_KEY` alterada para produção
- [ ] Banco de dados configurado
- [ ] Migrações aplicadas (`python manage.py migrate`)
- [ ] Arquivos estáticos coletados (`python manage.py collectstatic`)
- [ ] Gunicorn instalado e configurado
- [ ] Nginx configurado
- [ ] Serviço iniciado e funcionando
- [ ] Testar acesso à aplicação

## 🔧 Comandos Úteis

```bash
# Verificar status do serviço
sudo systemctl status habitas

# Ver logs do Gunicorn
sudo journalctl -u habitas -f

# Recarregar configuração do Nginx
sudo nginx -t
sudo systemctl reload nginx

# Recarregar aplicação Django
sudo systemctl restart habitas

# Verificar processos Python
ps aux | grep gunicorn
```

## 🆘 Solução de Problemas

### Erro: "No module named 'django'"
- Verifique se o ambiente virtual está ativado
- Execute `pip install -r requirements.txt`

### Erro: "DisallowedHost"
- Verifique se o domínio está em `ALLOWED_HOSTS` no settings.py

### Arquivos estáticos não aparecem
- Execute `python manage.py collectstatic`
- Verifique se `STATIC_ROOT` está configurado
- Verifique permissões da pasta `staticfiles/`

### Erro de migração
- Verifique se todas as migrações estão na pasta `main/migrations/`
- Execute `python manage.py makemigrations` se necessário
- Execute `python manage.py migrate`

## 📝 Notas Importantes

1. **Segurança**: Nunca deixe `DEBUG = True` em produção
2. **SECRET_KEY**: Use uma chave diferente em produção
3. **Banco de Dados**: Use PostgreSQL ou MySQL em produção (não SQLite)
4. **HTTPS**: Configure SSL/TLS para produção
5. **Backup**: Configure backups regulares do banco de dados

## 📞 Suporte

Em caso de dúvidas, consulte:
- Documentação Django: https://docs.djangoproject.com/
- Documentação Gunicorn: https://docs.gunicorn.org/
- Documentação Nginx: https://nginx.org/en/docs/

---

**Última atualização**: Data do deploy
**Versão**: Verificar tag Git ou versão no código

