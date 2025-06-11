from concurrent import futures
import grpc
import kvstore_pb2
import kvstore_pb2_grpc

class KVStoreServicer(kvstore_pb2_grpc.KVStoreServicer):
    def __init__(self):
        self.store = {}
        self.stats = {'sets': 0, 'gets': 0, 'getprefixes': 0}

    def set(self, request, context):
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

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    kvstore_pb2_grpc.add_KVStoreServicer_to_server(KVStoreServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("🔔 Servidor gRPC corriendo en puerto 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()