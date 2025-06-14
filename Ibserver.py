from concurrent import futures
import grpc
import kvstore_pb2
import kvstore_pb2_grpc
import os, io
import threading
import sys

# --- Configuración para la ubicación del log ---
if getattr(sys, 'frozen', False):
    # Si se ejecuta como ejecutable (congelado), obtener la carpeta del ejecutable.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # En desarrollo, la carpeta será donde se encuentra este script.

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "kvstore_data.log")


class KVStoreServicer(kvstore_pb2_grpc.KVStoreServicer):
    def __init__(self):
        self.store  = {}
        self.stats  = {'sets': 0, 'gets': 0, 'getprefixes': 0}
        self.log_file = LOG_FILE
        self._ensure_log_and_load()
        self._log_lock = threading.Lock() 

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

    def _append_to_log(self, key, value):
        """
        Escribe la línea SET|key|value al final del archivo de log
        de forma atómica para todos los hilos.
        """
        line = f"SET|{key}|{value}\n"
        with self._log_lock:                   #  ← NUEVO
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())           # fuerza a disco (durabilidad real)


    # ----------  RPCs  ----------
    def set(self, request, context):
        self._append_to_log(request.key, request.value)
        self.store[request.key] = request.value
        self.stats['sets'] += 1
        return kvstore_pb2.Empty()

    def get(self, request, context):
        self.stats['gets'] += 1
        value = self.store.get(request.key, "")
        return kvstore_pb2.GetResponse(value=value)

    def getPrefix(self, request, context):
        self.stats['getprefixes'] += 1
        vals = [v for k, v in self.store.items() if k.startswith(request.prefixKey)]
        return kvstore_pb2.GetPrefixResponse(values=vals)

    def stat(self, request, context):
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


