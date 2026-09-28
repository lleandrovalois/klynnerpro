FROM python:3.12-slim

# Evita geração de arquivos .pyc e ativa buffer imediato de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para libqpdf / gráficos e conversão LibreOffice headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libreoffice-writer-nogui \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copia requisitos e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Garante a existência do diretório temporário
RUN mkdir -p temp_workspaces

# Porta padrão exposta
EXPOSE 8000

# Executa o servidor vinculando à porta dinâmica fornecida pelo Render ($PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
