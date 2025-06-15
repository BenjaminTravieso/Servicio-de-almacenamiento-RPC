import grpc
import kvstore_pb2
import kvstore_pb2_grpc
import argparse
import random
import string
import sys

DEFAULT_NUM_OPERATIONS = 10

DEFAULT_NUM_OPERATIONS = 10
DEFAULT_SET_RATIO = 0.5 # 50% Sets, 50% Gets
DEFAULT_PREFIX_PROB = 0.05 # 5% chance of getPrefix
DEFAULT_STAT_PROB = 0.01 # 1% chance of stat


def generate_random_string(length=10):
    """Genera una cadena aleatoria de la longitud especificada."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


#----------------Para crear el script automáticamente----------------
def run_non_interactive(num_operations, set_ratio, prefix_prob, stat_prob):
    """
    Ejecuta el cliente en modo no interactivo, realizando un número específico de
    operaciones Set y Get.
    """
    with grpc.insecure_channel('127.0.0.1:50051') as channel:
        try:
            grpc.channel_ready_future(channel).result(timeout=5)
            print("✔ Conectado al servidor gRPC en 127.0.0.1:50051")
        except grpc.FutureTimeoutError:
            print("❌ No se pudo conectar al servidor en 127.0.0.1:50051")
            return

        stub = kvstore_pb2_grpc.KVStoreStub(channel)
        
        # Lista para almacenar las claves que se han establecido establecido para poder recuperarlas
        set_keys = []

        print(f"Iniciando {num_operations} operaciones en modo no interactivo...")

        for i in range(num_operations):
            op_type = random.random()

            if op_type < set_ratio: # Realizar una operación Set
                key = generate_random_string(8)
                value = generate_random_string(15)
                try:
                    stub.set(kvstore_pb2.KeyValue(key=key, value=value))
                    set_keys.append(key)
                except grpc.RpcError as e:
                    print(f"  [{i+1}/{num_operations}] ❌ Error en Set para '{key}': {e.details()}")
            
            elif op_type < set_ratio + prefix_prob: # Realizar una operación Prefix
                if set_keys:
                    prefix_to_get = random.choice(set_keys)[:random.randint(1, min(len(set_keys[0]), 5))] # Prefijo aleatorio de una clave existente
                    try:
                        resp = stub.getPrefix(kvstore_pb2.Prefix(prefixKey=prefix_to_get))
                    except grpc.RpcError as e:
                        print(f"  [{i+1}/{num_operations}] ❌ Error en getPrefix para '{prefix_to_get}': {e.details()}")
                else:
                    # print(f"  [{i+1}/{num_operations}] ⚠ No hay claves para realizar GetPrefix. Saltando operación.")
                    pass # Evita imprimir esto muchas veces si no hay claves
            
            elif op_type < set_ratio + prefix_prob + stat_prob: # Realizar una operación Stat
                try:
                    stats = stub.stat(kvstore_pb2.Empty())
                except grpc.RpcError as e:
                    print(f"  [{i+1}/{num_operations}] ❌ Error en stat: {e.details()}")
            
            else: # Realizar una operación Get
                if set_keys:
                    key_to_get = random.choice(set_keys)
                    try:
                        resp = stub.get(kvstore_pb2.Key(key=key_to_get))
                    except grpc.RpcError as e:
                        print(f"  [{i+1}/{num_operations}] ❌ Error en Get para '{key_to_get}': {e.details()}")
                else:
                    pass # Evitar imprimir esto muchas veces si no hay claves
            
            # Mensaje de progreso para 10K operaciones
            if (i + 1) % 1000 == 0:
                sys.stdout.write(f"\r  Cliente en progreso: {i+1}/{num_operations} operaciones...")
                sys.stdout.flush()

        sys.stdout.write(f"\rCompletadas {num_operations} operaciones por el cliente.               \n")
        sys.stdout.flush()



#----------------Para usar un menú que permita escrituras y lecturas----------------
def run_interactive():
    """
    Ejecuta el cliente en modo interactivo, solicitando la entrada del usuario
    para realizar operaciones. (Tu código original)
    """
    # Conectamos con el servidor gRPC
    with grpc.insecure_channel('127.0.0.1:50051') as channel:
        try:
            # Esperar hasta que el canal esté listo (timeout 5s)
            grpc.channel_ready_future(channel).result(timeout=5)
        except grpc.FutureTimeoutError:
            print("❌ No se pudo conectar al servidor en 127.0.0.1:50051")
            return

        stub = kvstore_pb2_grpc.KVStoreStub(channel)

        # Bucle de menú interactivo
        while True:
            print("\n===== Cliente KVStore =====")
            print("1) Set   – Establecer clave y valor")
            print("2) Get   – Consultar valor por clave")
            print("3) Prefix – Listar valores por prefijo")
            print("4) Stat  – Ver estadísticas del servidor")
            print("q) Salir")
            opcion = input("Selecciona una opción: ").strip().lower()

            if opcion == '1':
                key = input("→ Clave: ").strip()
                value = input("→ Valor: ").strip()
                try:
                    stub.set(kvstore_pb2.KeyValue(key=key, value=value))
                    print(f"✔ Set exitoso: '{key}' = '{value}'")
                except grpc.RpcError as e:
                    print("❌ Error en set:", e.details())

            elif opcion == '2':
                key = input("→ Clave a consultar: ").strip()
                try:
                    resp = stub.get(kvstore_pb2.Key(key=key))
                    print(f"✔ Get '{key}' → '{resp.value}'")
                except grpc.RpcError as e:
                    print("❌ Error en get:", e.details())

            elif opcion == '3':
                prefix = input("→ Prefijo de clave: ").strip()
                try:
                    resp = stub.getPrefix(kvstore_pb2.Prefix(prefixKey=prefix))
                    print(f"✔ Keys que empiezan con '{prefix}':")
                    for v in resp.values:
                        print("    -", v)
                except grpc.RpcError as e:
                    print("❌ Error en getPrefix:", e.details())

            elif opcion == '4':
                try:
                    stats = stub.stat(kvstore_pb2.Empty())
                    print("📊 Estadísticas del servidor:")
                    print("    total_sets        =", stats.total_sets)
                    print("    total_gets        =", stats.total_gets)
                    print("    total_getprefixes =", stats.total_getprefixes)
                except grpc.RpcError as e:
                    print("❌ Error en stat:", e.details())

            elif opcion == 'q':
                print("👋 Saliendo del cliente.")
                break

            else:
                print("⚠ Opción no reconocida. Intenta de nuevo.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Cliente KVStore para operaciones interactivas o no interactivas.")
    parser.add_argument(
        '-n', '--num-operations', type=int,
        help=f"Número de operaciones a realizar en modo no interactivo. Predeterminado: {DEFAULT_NUM_OPERATIONS}.",
        default=DEFAULT_NUM_OPERATIONS
    )

    parser.add_argument(
        '-i', '--interactive', action='store_true',
        help="Ejecuta el cliente en modo interactivo (predeterminado si no se especifica --num-operations)."
    )
    
    parser.add_argument(
        '--set-ratio', type=float,
        help="Proporción de operaciones Set en modo no interactivo (0.0 a 1.0). Prederminado: {DEFAULT_SET_RATIO}",
        default=DEFAULT_SET_RATIO
    )

    parser.add_argument(
        '--prefix-prob', type=float,
        help="Proporción de operaciones getPrefix en modo no interactivo (0.0 a 1.0). Prederminado: {DEFAULT_PREFIX_PROB}",
        default=DEFAULT_PREFIX_PROB
    )

    parser.add_argument(
        '--stat-prob', type=float,
        help="Proporción de operaciones Set en modo no interactivo (0.0 a 1.0). Prederminado: {DEFAULT_STAT_PROB}",
        default=DEFAULT_STAT_PROB
    )

    args = parser.parse_args()

    if args.interactive:
        print("Iniciando cliente en modo interactivo...")
        run_interactive()
    else:
        print(f"Iniciando cliente en modo no interactivo con {args.num_operations} operaciones...")
        run_non_interactive(args.num_operations, args.set_ratio, args.prefix_prob, args.stat_prob)
