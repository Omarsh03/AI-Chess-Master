# Reused Infrastructure Components

- `network.py` is kept as the socket transport abstraction.
- `timer_manager.py` is kept as the time-control abstraction.
- `server.py` and `client.py` now use full-chess result messages while preserving the same connection lifecycle:
  - connect
  - setup
  - time
  - mode
  - begin
  - move/result/exit
