#!/bin/bash

APP_NAME="app.py"
PID_FILE="app.pid"
LOG_FILE="app.log"
HOST="0.0.0.0"
PORT="8000"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "Chainlit is already running (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    nohup chainlit run $APP_NAME --host $HOST --port $PORT > $LOG_FILE 2>&1 & echo $! > $PID_FILE
    echo "Started Parliament Assistant AI (PID: $(cat $PID_FILE))"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        kill $(cat $PID_FILE)
        rm $PID_FILE
        echo "Stopped Parliament Assistant AI"
    else
        echo "Parliament Assistant AI is not running"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        echo "Parliament Assistant AI is running (PID: $(cat $PID_FILE))"
    else
        echo "Parliament Assistant AI is not running"
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; start ;;
    status)  status ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac