
import subprocess
import sys
import os

import grpc
import kvstore_pb2
import kvstore_pb2_grpc
import time
import signal
import random

SERVER_FILE = "Ibserver.py"
CLIENT_FILE = "Ibclient.py"
NUM_CLIENTS = 2                    #Cantidad de clientes
NUM_OPERATIONS_PER_CLIENT = 10000   #10K operaciones por cliente


def start_grpc_server():
    """
    Inicia el servidor gRPC como un proceso separado.
    """
    print(f"Intentando iniciar el servidor gRPC desde {SERVER_FILE}...")
    try:
        # Usa subprocess.Popen para iniciar el servidor de forma no bloqueante
        # Esto permite que el script de inicio termine, pero el servidor siga corriendo
        process = subprocess.Popen([sys.executable, SERVER_FILE])
        print(f"Servidor gRPC iniciado con PID: {process.pid}")
        print("Presiona Ctrl+C para detener el servidor (puede que necesites hacerlo en la ventana del servidor también).")
        time.sleep(2) #Toma un momento para inicializar el servidor
        
        return process

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{SERVER_FILE}'. Asegúrate de que la ruta sea correcta.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error al iniciar el servidor: {e}")
        sys.exit(1)



def start_grpc_client(client_id, num_operations, set_ratio, prefix_prob, stat_prob):
    """
    Se empieza un cliente gRPC como un proceso separado para realizar operaciones
    con proporciones especificadas
    """
    print(f"Empezando cliente {client_id} para empezar {num_operations} operaciones (Set: {set_ratio*100:.0f}%, Prefix: {prefix_prob*100:.0f}%, Stat: {stat_prob*100:.0f}%... ")
    try:
        # Pasa los argumentos de proporción al cliente
        command = [
            sys.executable, CLIENT_FILE, 
            '--num-operations', str(num_operations),
            '--set-ratio', str(set_ratio),
            '--prefix-prob', str(prefix_prob),
            '--stat-prob', str(stat_prob)
        ]
        process = subprocess.Popen(command)
        return process
    
    except FileNotFoundError:
        print(f"Error: Archivo de Cliente '{CLIENT_FILE}' no encontrado. Asegurese que la ruta es correcta. ")
        return None
    except Exception as e:
        print(f"Un error ha ocurrido mientras empezaba el client {client_id}: {e}")
        return None



def stop_grpc_server(server_process):
    """
    Detiene los procesos del servidor gRPC.
    """
    if server_process and server_process.poll() is None: # Se verifica que los procesos estén todavía en ejecucion
        print(f"Intentando detener el servidor gRPC con PID: {server_process.pid}...")
        try:
            # Enviar una señal para terminar
            server_process.terminate()
            server_process.wait(timeout=5) # Esperar que el proceso termine
            if server_process.poll() is None:
                print(f"El servidor no terminó correctamente, cerrando PID: {server_process.pid}...")
                server_process.kill()
            print("Servidor gRPC detenido.")
        except Exception as e:
            print(f"Error deteniendo el servidor: {e}")
    else:
        print("Servidor gRPC no estaba ejecutándose o ya estaba detenido")


def get_server_statistics():
    """
    Se conecta al servidor gRPC y obtiene las estadísticas actuales.
    """
    server_address = '127.0.0.1:50051'
    with grpc.insecure_channel(server_address) as channel:
        try:
            # Esperar a que el canal esté listo, con un timeout
            grpc.channel_ready_future(channel).result(timeout=5)
            print(f"✔ Conectado al servidor gRPC en {server_address} para obtener estadísticas.")
        except grpc.FutureTimeoutError:
            print(f"❌ No se pudo conectar al servidor en {server_address} para obtener estadísticas.")
            return None

        stub = kvstore_pb2_grpc.KVStoreStub(channel)
        try:
            # Llamar al método stat en el servidor
            stats = stub.stat(kvstore_pb2.Empty())
            return stats
        except grpc.RpcError as e:
            print(f"❌ Error al obtener estadísticas del servidor: {e.details()}")
            return None




if __name__ == "__main__":    
    server_process = None
    client_processes = []
    start_time = time.time()
    server_start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))

    try:
        # 1. Inicia el servidor gRPC
        server_process = start_grpc_server()
        if not server_process:
            sys.exit(1)

        # 2. Inicia varios clientes gRPC con proporciones aleatorias de operaciones
        print(f"\nEmpezando {NUM_CLIENTS} clientes para  {NUM_OPERATIONS_PER_CLIENT} operaciones cada uno...")
        
        for i in range(NUM_CLIENTS):
            #Generar proporciones aleatorias para cada cliente
            set_ratio = random.uniform(0.3, 0.7) # Por ejemplo, entre 30% y 70% Sets
            remaining_prob = 1.0 - set_ratio
            
            # Distribuir el resto entre Get, Prefix y Stat
            prefix_prob = random.uniform(0, remaining_prob * 0.1) # Hasta el 10% del restante para Prefix
            remaining_after_prefix = remaining_prob - prefix_prob
            
            stat_prob = random.uniform(0, remaining_after_prefix * 0.05) # Hasta el 5% del restante para Stat
            
            # El resto será para Get (implícitamente)
            # La lógica en Ibclient.py maneja el resto como Gets
            
            client_proc = start_grpc_client(
                i + 1, 
                NUM_OPERATIONS_PER_CLIENT,
                set_ratio,
                prefix_prob,
                stat_prob
            )
            
            
            if client_proc:
                client_processes.append(client_proc)
            time.sleep(0.1) #Pequeña pausa para evitar que todos los clientes arranquen al mismo tiempo 

        # 3. Espera a que todos los clientes sean completados
        print("\nEsperando que los clientes completen sus operaciones...")
        for client_proc in client_processes:
            client_proc.wait() # Esto se bloqueará hasta que finalice el proceso del cliente
            print(f"Cliente {client_proc.pid} ha finalizado.")
    

        # 4. Solicitud de estadísticas desde el servidor (¡Ahora real!)
        print("\nSolicitando estadísticas reales del servidor...")
        server_stats = get_server_statistics() # Llama a la nueva función

        # 5. Muestra estadísticas
        print("\n--- Estadisticas de Operaciones ---")
        print(f"Hora de Inicio del Servidor: {server_start_time_str}")
        if server_stats:
            print(f"Total Sets Completados: {server_stats.total_sets}")
            print(f"Total Gets Completados: {server_stats.total_gets}")
            print(f"Total GetPrefixes Completados: {server_stats.total_getprefixes}")
        else:
            print("No se pudieron obtener las estadísticas del servidor.")
    
    except KeyboardInterrupt:
        print("\nScript interrumpido por el usuario. Apagando...")
    finally:
        # segurarse de que el servidor se detenga incluso si se produce un error o se interrumpe el script.
        stop_grpc_server(server_process)
        print("Script finalizado.")
    #start_grpc_server()