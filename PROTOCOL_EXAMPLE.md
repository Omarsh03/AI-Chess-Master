# Chess Game Protocol Example

This document shows an example of successful client-server communication in our chess game.

## Server-Client Communication Flow

### Initial Connection
```
Client: Connected to server!
Server: Setup Wa2 Wb2 Wc2 Wd2 We2 Wf2 Wg2 Wh2 Ba7 Bb7 Bc7 Bd7 Be7 Bf7 Bg7 Bh7
Client: OK
Server: Time 30
Client: OK
```

### Game Start and Moves
```
Server: e2e4
Client: OK
Client: e7e5
Server: OK
```

### Game End
```
Server: exit
Client: Connection closed
Server: Session ended
Bytes written: 80 Bytes read: 32649
Elapsed time: 82 secs
```

## Protocol Rules

1. Initial Setup:
   - Server sends setup command with initial position
   - Client must respond with "OK"
   - Server sends time control (in minutes)
   - Client must respond with "OK"

2. During Game:
   - Moves are sent in standard chess notation (e.g., "e2e4")
   - Each move must be acknowledged with "OK"
   - Server can send "exit" to terminate the game

3. Move Format:
   - Source square + destination square (e.g., "e2e4")
   - No special characters or additional formatting
   - Case sensitive

4. Error Handling:
   - Invalid moves result in game termination
   - Connection errors result in session end
   - Time-out results in game end

## Example Game Session Log

Here's a complete example of a server output during a successful game:

```
Server listening on 127.0.0.1:9999
New connection from ('127.0.0.1', 52431)
Client connected and responded: OK
Setup sent, client responded: OK
Time 30 minutes sent, client responded: OK
White moves: e2e4 (29:45 remaining)
Black moves: e7e5 (29:30 remaining)
Game ended normally
Connection closed
```

This protocol follows the requirements specified in the original TCP/IP protocol document, ensuring proper game initialization, move validation, and session management. 