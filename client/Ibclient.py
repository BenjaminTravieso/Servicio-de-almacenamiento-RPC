import grpc
import kvstore_pb2, kvstore_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub   = kvstore_pb2_grpc.KVStoreStub(channel)

    # Prueba de set/get
    stub.set(kvstore_pb2.KeyValue(key='foo', value='bar'))
    resp = stub.get(kvstore_pb2.Key(key='foo'))
    print("get foo ->", resp.value)

    # Prueba de getPrefix
    stub.set(kvstore_pb2.KeyValue(key='fizz', value='buzz'))
    pref = stub.getPrefix(kvstore_pb2.Prefix(prefixKey='f'))
    print("getPrefix 'f' ->", pref.values)

    # Estadísticas
    stats = stub.stat(kvstore_pb2.Empty())
    print("stats ->", stats)

if __name__ == '__main__':
    run()