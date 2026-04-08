import threading
from src.pc1.broker_zmq import main as broker_main
from src.pc1.main_pc1 import main as sensores_main

if __name__ == "__main__":
    hilo_broker = threading.Thread(target=broker_main, daemon=True)
    hilo_broker.start()

    sensores_main()