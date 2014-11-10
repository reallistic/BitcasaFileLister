import os, sys, logging, threading, webbrowser, time, argparse
insert_path = os.path.abspath("./includes/")
sys.path.append(insert_path)
insert_path = os.path.abspath("./includes/lib/")
sys.path.append(insert_path)
import server
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)s][%(levelname)s]: %(message)s', datefmt='%m/%d %H:%M:%S')
log = logging.getLogger("BitcasaFileLister")

def open_browser(cancel_open):
    time.sleep(5)
    if not cancel_open.is_set():
        webbrowser.open("http://localhost:1115/bitcasafilelister/")

if __name__ == '__main__':
    mainparser = argparse.ArgumentParser(prog="BitcasaFileLister", description="List files in Bitcasa")
    mainparser.add_argument("-n","--nolaunch", help="Don't launch browser", action="store_true")
    args = mainparser.parse_args()
    cancel_open = threading.Event()
    if not args.nolaunch:
        threading.Thread(target=open_browser, args=(cancel_open, )).start()
    try:
        if not args.nolaunch:
            log.info("Your browser will open in 5 seconds. To disable this. Run with param --nolaunch")
        server.start()
    except:
        cancel_open.set()