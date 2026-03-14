import time
import logging
from queue_listener import listen_for_tasks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("Starting Python Agent Worker...")
    while True:
        try:
            listen_for_tasks()
        except Exception as e:
            logging.error(f"Error in worker loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
