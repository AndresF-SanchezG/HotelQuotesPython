from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime
import os

app = FastAPI()

origins = ["http://104.198.178.240:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

dataFrameHoteles = pd.read_excel('./Libro1.xlsx')

dataFrameHoteles['Desde'] = pd.to_datetime(dataFrameHoteles['Desde'])
dataFrameHoteles['Hasta*'] = pd.to_datetime(dataFrameHoteles['Hasta*'])

def save_uploaded_file(file: UploadFile, destination: str):
    with open(destination, "wb") as file_object:
        file_object.write(file.file.read())

def delete_file(file_path: str):
    if os.path.exists(file_path):
        os.remove(file_path)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto+Mono:wght@400;500&family=Roboto+Slab:wght@500;600&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="" type="text/css">
        <title>Plenty APP</title>
    </head>
    <body>
        <div class="container">
            <h1>ATERRIZA APP - MODULO ADMINISTRATIVO</h1>
            <h3>Sección: Carga de Facturas</h3>
            <div class="view">
                <h4></h4>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="excel_file" accept=".xls, .xlsx">
                    <input type="submit" value="Subir Excel">
                </form>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/upload/")
async def upload_file(excel_file: UploadFile = File(...)):
    # Eliminar el archivo existente si hay uno
    delete_file("Libro1.xlsx")

    # Guardar el nuevo archivo
    save_uploaded_file(excel_file, "Libro1.xlsx")
    
    return {"filename": excel_file.filename}

@app.post("/api/cotizar")
def cotizar(data: dict):

    # Obtener los datos proporcionados
    hotel = data.get('hotel', '')
    fecha_entrada = data.get('fecha_entrada', '')
    fecha_salida = data.get('fecha_salida', '')
    cantidad_adultos = data.get('cantidad_adultos', 0)
    cantidad_ninos = data.get('cantidad_ninos', 0)

    # Validar y sanitizar los datos según sea necesario

    # Definir las fechas de entrada y salida
    fecha_desde = datetime.strptime(fecha_entrada, '%Y-%m-%d')
    fecha_hasta = datetime.strptime(fecha_salida, '%Y-%m-%d')

    # Filtrar por Hotel y fechas
    filtro = (dataFrameHoteles['Hotel'] == hotel) & (dataFrameHoteles['Desde'] <= fecha_hasta) & (dataFrameHoteles['Hasta*'] >= fecha_desde)
    df_filtrado = dataFrameHoteles[filtro].copy()

    
    # Calcular la nueva columna cant_dias utilizando .apply
    df_filtrado['cant_dias'] = df_filtrado.apply(lambda row: (min(row['Hasta*'], fecha_hasta) - max(row['Desde'], fecha_desde)).days + 1, axis=1)

    # Identificar la última fila de cada grupo de habitaciones y restar 1 solo a esa fila
    last_rows = df_filtrado.duplicated(subset='Habitación', keep='last')
    df_filtrado.loc[df_filtrado.index.isin(last_rows[last_rows == False].index), 'cant_dias'] -= 1

    # Agregar las columnas cant_adultos y cant_niños con valores proporcionados
    df_filtrado['cant_adultos'] = int(cantidad_adultos)
    df_filtrado['cant_niños'] = int(cantidad_ninos)

    # Corregir la condición para calcular valor_adultos correctamente
    df_filtrado['valor_adultos'] = df_filtrado.apply(lambda row: row['cant_dias'] * row['Sencilla'] * row['cant_adultos'] if row['cant_adultos'] == 1 and row['cant_niños'] == 0 else row['cant_dias'] * row['Doble/Adicional'] * row['cant_adultos'], axis=1)

    # Corregir la condición para calcular valor_niños correctamente
    df_filtrado['valor_niños'] = df_filtrado.apply(lambda row: row['cant_dias'] * row['Niño'] * row['cant_niños'] if row['cant_niños'] > 0 and row['cant_adultos'] > 0 else 0, axis=1)

    # Obtener el resultado como un DataFrame con las nuevas columnas
    resultado_df = df_filtrado[['Hotel', 'Habitación', 'Desde', 'Hasta*', 'Descuento', 'Sencilla', 'Doble/Adicional', 'Niño', 'cant_adultos', 'cant_niños', 'valor_adultos', 'valor_niños']]

    # Agrupar solo por Habitación y sumar las columnas relevantes
    resumen_totalizado = resultado_df.groupby(['Hotel', 'Habitación']).agg({
        'cant_adultos': 'first',  # Tomar el primer valor, ya que todos son iguales
        'cant_niños': 'first',   # Tomar el primer valor, ya que todos son iguales
        'valor_adultos': 'sum',
        'valor_niños': 'sum',
        'Desde': lambda x: fecha_entrada,   # Utilizar fecha_entrada para todas las filas agrupadas
        'Hasta*': lambda x: fecha_salida    # Utilizar fecha_salida para todas las filas agrupadas
    }).reset_index()
    

    # Calcular el valor_total como la suma de valor_adultos y valor_niños
    resumen_totalizado['valor_total'] = resumen_totalizado['valor_adultos'] + resumen_totalizado['valor_niños']

    resumen_totalizado['cant_adultos'] = resumen_totalizado['cant_adultos'].astype(int)
    resumen_totalizado['cant_niños'] = resumen_totalizado['cant_niños'].astype(int)
    resumen_totalizado['valor_adultos'] = resumen_totalizado['valor_adultos'].astype(int)
    resumen_totalizado['valor_niños'] = resumen_totalizado['valor_niños'].astype(int)
    resumen_totalizado['valor_total'] = resumen_totalizado['valor_total'].astype(int)

    # Agregar una nueva columna que sume cant_adultos y cant_niños
    resumen_totalizado['cant_total'] = resumen_totalizado['cant_adultos'] + resumen_totalizado['cant_niños']


    # Imprimir el nuevo DataFrame resumen_totalizado
    print(resultado_df)
    print(resumen_totalizado)

    # Convertir el DataFrame resumen_totalizado a un diccionario JSON
    resultado_json = resumen_totalizado.to_dict(orient='records')

    return {'resultado': resultado_json}

if __name__ == '__main__':
    import uvicorn
  
    uvicorn.run(app, host="0.0.0.0", port=5000)





