import grpc
import kvstore_pb2
import kvstore_pb2_grpc

def run_interactive():
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
                        print("   -", v)
                except grpc.RpcError as e:
                    print("❌ Error en getPrefix:", e.details())

            elif opcion == '4':
                try:
                    stats = stub.stat(kvstore_pb2.Empty())
                    print("📊 Estadísticas del servidor:")
                    print("   total_sets       =", stats.total_sets)
                    print("   total_gets       =", stats.total_gets)
                    print("   total_getprefixes=", stats.total_getprefixes)
                except grpc.RpcError as e:
                    print("❌ Error en stat:", e.details())

            elif opcion == 'q':
                print("👋 Saliendo del cliente.")
                break

            else:
                print("⚠ Opción no reconocida. Intenta de nuevo.")

if __name__ == '__main__':
    run_interactive()