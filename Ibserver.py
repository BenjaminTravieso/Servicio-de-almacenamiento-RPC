import os
import threading
import grpc
from concurrent import futures
import kvstore_pb2
import kvstore_pb2_grpc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "kvstore_data.log")
ONE_DAY_IN_SECONDS = 60 * 60 * 24


class KVStoreServicer(kvstore_pb2_grpc.KVStoreServicer):
    def __init__(self):
        self.store  = {}
        #Diccionario para almacenar estadisticas
        self.stats  = {'sets': 0, 'gets': 0, 'getprefixes': 0, } 
        self.log_file = LOG_FILE
        #Cargar los datos
        self._ensure_log_and_load()
        self._log_lock = threading.Lock()  # Mecanismo de sincronización de clientes



    # ----------  DURABILIDAD  ----------
    def _ensure_log_and_load(self):
        """
        1. Abre el fichero en modo a+  (lo crea si no existe).
        2. Lee todas las líneas para reconstruir el diccionario.
        """
        # “a+” = crea si no existe, posiciona al final; luego hacemos seek(0) para leer.
        with open(self.log_file, "a+", encoding="utf-8") as f:
            f.seek(0)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                label, key, value = line.split("|", 2)
                if label == "SET":
                    self.store[key] = value
        print(f"🗂  Estado reconstruido: {len(self.store)} claves cargadas.")


    # Guardar las nuevas lecturas y escrituras en el archivo  ----------
    """
        Escribe la línea SET|key|value al final del archivo de log
        de forma atómica para todos los hilos.
    """
    def _append_to_log(self, key, value):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"SET|{key}|{value}\n")
    

    # ----------  RPCs  ----------
    def set(self, request, context):
        with self._log_lock:
            self._append_to_log(request.key, request.value)
            self.store[request.key] = request.value
            self.stats['sets'] += 1
        return kvstore_pb2.Empty()

    def get(self, request, context):
        with self._log_lock:
            self.stats['gets'] += 1
            value = self.store.get(request.key, "")
        return kvstore_pb2.GetResponse(value=value)

    def getPrefix(self, request, context):
        with self._log_lock:
            self.stats['getprefixes'] += 1
            vals = [v for k, v in self.store.items() if k.startswith(request.prefixKey)]
        return kvstore_pb2.GetPrefixResponse(values=vals)



    def stat(self, request, context):
        with self._log_lock:
            total_sets=self.stats['sets'],
            total_gets=self.stats['gets'],
            total_getprefixes=self.stats['getprefixes']

            current_sets = self.stats['sets']
            current_gets = self.stats['gets']
            current_getprefixes = self.stats['getprefixes']
        return kvstore_pb2.StatResponse(
            total_sets=self.stats['sets'],
            total_gets=self.stats['gets'],
            total_getprefixes=self.stats['getprefixes']
        )

# ----------  BOILERPLATE  ----------
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    kvstore_pb2_grpc.add_KVStoreServicer_to_server(KVStoreServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("🔔 Servidor gRPC corriendo en puerto 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()