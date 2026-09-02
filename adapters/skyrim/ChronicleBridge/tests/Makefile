# Standalone test harness for SyncHandshakeCore -- the pure, SKSE-independent
# half of the save/reload sync-handshake state machine (spec doc §5's hard
# requirement: docs/design/chronicle-bridge-sync-handshake-out.md) -- plus
# SyncHelloResponseParser, the ONE genuinely new hand-rolled component the
# glue layer (SyncHandshake.h/.cpp) needed that could still be factored to
# be SKSE-independent (see that file's own header comment for why).
#
# Deliberately NOT wired into ../CMakeLists.txt: that build requires
# vcpkg + CommonLibSSE + a Windows/cross toolchain (see ../README.md) and
# precompiles src/PCH.h, which would risk pulling SKSE headers into this
# translation unit. This test only needs a standard-library-only g++/clang++
# -- that independence is the entire point of the pure-core split (spec §5).
#
# Usage:
#   make        # build + run
#   make build  # build only -> ./test_sync_handshake_core
#   make clean

CXX      ?= g++
CXXFLAGS ?= -std=c++20 -Wall -Wextra -Wpedantic -O1
SRC      := ../src/SyncHandshakeCore.cpp ../src/SyncHelloResponseParser.cpp test_sync_handshake_core.cpp
BIN      := test_sync_handshake_core

.PHONY: all build run clean

all: run

build: $(BIN)

$(BIN): $(SRC) ../src/SyncHandshakeCore.h ../src/SyncHelloResponseParser.h
	$(CXX) $(CXXFLAGS) -o $(BIN) $(SRC)

run: build
	./$(BIN)

clean:
	rm -f $(BIN)
