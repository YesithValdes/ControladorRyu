from fastapi import FastAPI,HTTPException, Request
from fastapi.responses import JSONResponse
import paramiko
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dirección del servidor Ryu
RYU_SERVER_IP = "192.168.101.72"  # Cambia esto a la IP de tu servidor Ryu
RYU_SERVER_PORT = 8080
RYU_BASE_URL = f"http://{RYU_SERVER_IP}:{RYU_SERVER_PORT}"
RYU_USER= "ryu"
RYU_PASS= "ryu"

# Variable para almacenar el proceso de Ryu
ryu_process = None

@app.post("/start-ryu")
async def start_ryu(request: Request):
    global ryu_process
    try:
        data = await request.json()  # Obtener los datos JSON del cuerpo de la solicitud
        app_name = data.get('app_name')
        my_string = data.get('my_string', "String no recibido")  # Obtener el string
        
        print(f"Recibido el string: {app_name}")  # Imprimir el string recibido
        # Conectar al servidor remoto via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=RYU_SERVER_IP, username=RYU_USER, password=RYU_PASS)

        # Ejecutar el comando ryu-manager con el app 'simple_switch.py'
        #command = "ryu-manager /usr/lib/python3/dist-packages/ryu/app/simple_switch.py"
        if(app_name=="topologia"):
            command = "ryu-manager --verbose --observe-links /usr/lib/python3/dist-packages/ryu/app/simple_switch_13.py /usr/lib/python3/dist-packages/ryu/app/rest_topology.py"
            
        else:
            command = f"ryu-manager /usr/lib/python3/dist-packages/ryu/app/{app_name}"
        
        ryu_process = ssh.exec_command(command, get_pty=True)  # Ejecuta el comando y obtiene el canal
        # Acceder al canal de stdin y stdout
        stdin, stdout, stderr = ryu_process

        return JSONResponse({"message": "Aplicación iniciada correctamente"})
    except Exception as e:
        return JSONResponse({"message": f"Error al iniciar la aplicación: {str(e)}"}, status_code=500)

@app.post("/stop-ryu")
async def stop_ryu():
    global ryu_process
    try:
        if ryu_process is not None:
            # Acceder al canal de stdin y escribir el comando de salida 'exit'
            stdin, stdout, stderr = ryu_process
            stdin.write('exit\n')
            stdin.flush()

            # Cerrar los canales
            stdout.channel.close()
            stderr.channel.close()

            return JSONResponse({"message": "Aplicación detenida correctamente"})
        else:
            return JSONResponse({"message": "La aplicación no está en ejecución"}, status_code=400)
    except Exception as e:
        return JSONResponse({"message": f"Error al detener la aplicación: {str(e)}"}, status_code=500)

@app.get("/v1.0/topology/links")
async def get_links():
    """
    Método para obtener la lista de enlaces de la topología desde el controlador Ryu.
    """
    try:
        # URL del endpoint de enlaces en Ryu
        url = f"{RYU_BASE_URL}/v1.0/topology/links"

        # Hacer una solicitud GET asincrónica al controlador Ryu
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Levanta una excepción si el código de estado no es 2xx
            return response.json()  # Devolver la respuesta como JSON

    except httpx.RequestError as e:
        # Capturar errores de conexión o solicitud
        raise HTTPException(status_code=500, detail=f"Error al conectar con el controlador Ryu: {e}")
    except httpx.HTTPStatusError as e:
        # Capturar errores de respuesta HTTP (como 404 o 500)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error desde el controlador Ryu: {e.response.text}"
        ) 

@app.get("/v1.0/topology/hosts")
async def get_links():
    """
    Método para obtener la lista de hosts de la topología desde el controlador Ryu.
    """
    try:
        # URL del endpoint de enlaces en Ryu
        url = f"{RYU_BASE_URL}/v1.0/topology/hosts"

        # Hacer una solicitud GET asincrónica al controlador Ryu
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()  # Levanta una excepción si el código de estado no es 2xx
            return response.json()  # Devolver la respuesta como JSON

    except httpx.RequestError as e:
        # Capturar errores de conexión o solicitud
        raise HTTPException(status_code=500, detail=f"Error al conectar con el controlador Ryu: {e}")
    except httpx.HTTPStatusError as e:
        # Capturar errores de respuesta HTTP (como 404 o 500)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error desde el controlador Ryu: {e.response.text}"
        )


@app.post("/stats/flowentry/add")
async def agregar_flujo(request: Request):
    """
    Método para agregar una entrada de flujo en el controlador Ryu.
    """
    try:
        # Obtener el JSON enviado por el cliente
        payload = await request.json()

        # URL del endpoint en el servidor Ryu
        url = f"{RYU_BASE_URL}/stats/flowentry/add"

        # Enviar la solicitud POST al controlador Ryu
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            # Intentar parsear la respuesta como JSON
            try:
                response_data = response.json()
            except ValueError:
                response_data = {"raw_response": response.text}

            return {
                "message": "Solicitud procesada con éxito en Ryu",
                "ryu_response": response_data,
            }

    except httpx.RequestError as e:
        # Capturar errores de conexión o solicitud
        raise HTTPException(status_code=500, detail=f"Error al conectar con el controlador Ryu: {e}")
    except httpx.HTTPStatusError as e:
        # Capturar errores de respuesta HTTP (como 404 o 500)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error desde el controlador Ryu: {e.response.text}"
        )
    except Exception as e:
        # Capturar otros errores internos
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")