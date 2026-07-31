FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que o Easypanel vai rodar (ajuste se seu app usar outra porta)
EXPOSE 5000

# Comando para rodar a aplicação
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
