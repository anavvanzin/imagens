FROM docker.io/cloudflare/sandbox:0.7.0

# Instalação de dependências de Python úteis para análise de dados do acervo
RUN pip install requests pandas openpyxl jsonschema

EXPOSE 8080
