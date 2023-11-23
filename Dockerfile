FROM python:3.8

WORKDIR /app

# Copia el archivo requeriments.txt al directorio de trabajo
COPY requeriments.txt /app/requeriments.txt

# Instala las dependencias especificadas en requirements.txt
RUN pip install --no-cache-dir -r requeriments.txt

COPY . /app

# Expone el puerto en el que la aplicación se ejecutará (asegúrate de que coincida con el puerto en tu aplicación)
EXPOSE 5000

CMD ["python", "main.py"]
