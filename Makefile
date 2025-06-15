#################################################################
# Makefile para tu KV-Store gRPC en Python
#################################################################

# VARIABLES
PROTO_DIR   := proto
OUT_DIR     := .
PROTOS      := $(PROTO_DIR)/kvstore.proto
PY_STUBS    := kvstore_pb2.py kvstore_pb2_grpc.py

# Targets por defecto
.PHONY: all help proto run-server run-client clean

all: proto
 @echo "Targets disponibles: proto, run-server, run-client, clean"

# Genera los stubs de Python a partir del .proto
proto: $(PY_STUBS)

$(PY_STUBS): $(PROTOS)
 @echo "🛠  Generando stubs gRPC a partir de $<"
 python -m grpc_tools.protoc \
 	-I$(PROTO_DIR) \
 	--python_out=$(OUT_DIR) \
 	--grpc_python_out=$(OUT_DIR) \
 	$<

# Arranca el servidor
run-server:
 @echo "🚀  Iniciando lbserver"
 python server/lbserver.py

# Arranca el cliente
run-client:
 @echo "📡  Iniciando lbclient"
 python client/lbclient.py

# Limpia archivos generados
clean:
 @echo "🧹  Limpiando artefactos"
 rm -f $(PY_STUBS)
 rm -rf __pycache__ *.pyc

# Ayuda
help:
 @echo ""
 @echo "Uso: make [target]"
 @echo ""
 @echo "Targets disponibles:"
 @echo "  all          → compila proto (por defecto)"
 @echo "  proto        → genera stubs de gRPC"
 @echo "  run-server   → ejecuta server/lbserver.py"
 @echo "  run-client   → ejecuta client/lbclient.py"
 @echo "  clean        → borra archivos generados"
 @echo ""