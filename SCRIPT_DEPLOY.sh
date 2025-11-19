#!/bin/bash
# Script de Deploy Automatizado - Habitas Arbor-e-ita
# Execute este script no servidor de produção

set -e  # Parar em caso de erro

echo "🚀 Iniciando deploy do Habitas Arbor-e-ita..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se está no diretório correto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Erro: manage.py não encontrado. Execute este script na raiz do projeto.${NC}"
    exit 1
fi

# Verificar Python
echo -e "${YELLOW}📦 Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado. Instale Python 3.8 ou superior.${NC}"
    exit 1
fi
python3 --version

# Ativar ambiente virtual (se existir)
if [ -d "venv" ]; then
    echo -e "${YELLOW}🔧 Ativando ambiente virtual...${NC}"
    source venv/bin/activate
fi

# Instalar/Atualizar dependências
echo -e "${YELLOW}📥 Instalando dependências...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}❌ requirements.txt não encontrado!${NC}"
    exit 1
fi

# Aplicar migrações
echo -e "${YELLOW}🗄️  Aplicando migrações do banco de dados...${NC}"
python manage.py migrate --noinput

# Coletar arquivos estáticos
echo -e "${YELLOW}📁 Coletando arquivos estáticos...${NC}"
python manage.py collectstatic --noinput

# Verificar configurações
echo -e "${YELLOW}⚙️  Verificando configurações...${NC}"
python manage.py check --deploy

echo -e "${GREEN}✅ Deploy concluído com sucesso!${NC}"
echo -e "${YELLOW}⚠️  Lembre-se de:${NC}"
echo "   1. Configurar DEBUG = False no settings.py"
echo "   2. Configurar ALLOWED_HOSTS"
echo "   3. Configurar SECRET_KEY"
echo "   4. Configurar banco de dados"
echo "   5. Reiniciar o serviço Gunicorn/Nginx"

