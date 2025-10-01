import threading
import requests
import time
import logging
import sys
from urllib.parse import urlparse
import signal
from datetime import datetime

# Configurações globais
REQUEST_COUNT = 0  # Contador de requisições
SUCCESS_COUNT = 0  # Contador de sucessos
ERROR_COUNT = 0    # Contador de erros
LOCK = threading.Lock()  # Lock pra contadores
STOP_EVENT = threading.Event()  # Evento pra parar threads
SERVER_DOWN = False  # Flag pra indicar se o servidor caiu

# Configura logging
log_file = f"ddos_test_{time.strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s"
)

def validate_url(url):
    """Valida se a URL é válida e acessível."""
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code >= 400:
            print(f"\033[91m[ERRO] URL {url} retornou erro {response.status_code}. Verifique o servidor.\033[0m")
            return None
        return url
    except requests.exceptions.RequestException as e:
        print(f"\033[91m[ERRO] URL {url} inválida ou servidor offline: {e}\033[0m")
        return None

def send_requests(url, max_requests_per_thread, method="GET", post_data=None):
    """Envia requisições HTTP até o limite, parada manual ou servidor cair."""
    global REQUEST_COUNT, SUCCESS_COUNT, ERROR_COUNT, SERVER_DOWN
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
    }
    count = 0

    while not STOP_EVENT.is_set() and count < max_requests_per_thread and not SERVER_DOWN:
        try:
            start_time = time.time()
            if method == "POST":
                response = requests.post(url, headers=headers, data=post_data, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)
            elapsed = time.time() - start_time
            with LOCK:
                REQUEST_COUNT += 1
                SUCCESS_COUNT += 1
                msg = f"Status {response.status_code} | Tempo: {elapsed:.2f}s | Método: {method}"
                logging.info(msg)
                print(f"\033[92m[{threading.current_thread().name}] {msg}\033[0m")
            if response.status_code >= 500:
                with LOCK:
                    SERVER_DOWN = True
                    msg = f"Servidor instável (Status {response.status_code}). Parando teste."
                    logging.warning(msg)
                    print(f"\033[91m[{threading.current_thread().name}] {msg}\033[0m")
        except requests.exceptions.RequestException as e:
            with LOCK:
                REQUEST_COUNT += 1
                ERROR_COUNT += 1
                msg = f"Erro: {e} | Método: {method}"
                logging.error(msg)
                print(f"\033[91m[{threading.current_thread().name}] {msg}\033[0m")
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    SERVER_DOWN = True
                    msg = f"Servidor caiu: {e}. Parando teste."
                    logging.warning(msg)
                    print(f"\033[91m[{threading.current_thread().name}] {msg}\033[0m")
        time.sleep(0.1)  # Delay pra evitar sobrecarga
        count += 1

def signal_handler(sig, frame):
    """Lida com Ctrl+C pra parar as threads."""
    print("\n\033[93m[AVISO] Interrompido pelo usuário. Finalizando...\033[0m")
    STOP_EVENT.set()
    time.sleep(1)
    print_report()

def print_report():
    """Exibe relatório final."""
    print(f"\n\033[94m{'='*50}\033[0m")
    print(f"\033[94mRelatório Final - {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\033[0m")
    print(f"Total de requisições: {REQUEST_COUNT}")
    print(f"Sucessos: {SUCCESS_COUNT}")
    print(f"Erros: {ERROR_COUNT}")
    if SERVER_DOWN:
        print("\033[91mTeste parado: Servidor não respondeu (possivelmente caiu).\033[0m")
    print(f"Log salvo em: {log_file}")
    print(f"\033[94m{'='*50}\033[0m")

def display_menu():
    """Exibe o menu interativo."""
    print("\033[96m" + "="*50 + "\033[0m")
    print("\033[96m         DDoS Test - Script de Teste de Estresse         \033[0m")
    print("\033[93mAVISO: Use APENAS em servidores próprios ou com autorização!\033[0m")
    print("\033[96m" + "="*50 + "\033[0m")
    print("1. Configurar e iniciar teste")
    print("2. Alterar método HTTP (GET/POST)")
    print("3. Sair")
    print("\033[96m" + "="*50 + "\033[0m")

def main():
    config = {
        "url": "http://127.0.0.1",
        "num_threads": 5,
        "max_requests": 100,
        "method": "GET",
        "post_data": None
    }

    while True:
        display_menu()
        choice = input("\033[92mEscolha uma opção (1-3): \033[0m").strip()

        if choice == "1":
            print("\n\033[93m[CONFIGURAÇÃO] Insira os parâmetros do teste:\033[0m")
            url = input("Digite o IP ou URL do servidor (ex: http://127.0.0.1): ").strip()
            url = validate_url(url)
            if not url:
                continue
            try:
                num_threads = int(input("Digite o número de threads (ex: 5): "))
                max_requests = int(input("Digite o número máximo de requisições por thread (ex: 100): "))
            except ValueError:
                print("\033[91m[ERRO] Insira números válidos.\033[0m")
                continue

            config["url"] = url
            config["num_threads"] = num_threads
            config["max_requests"] = max_requests

            # Reseta contadores
            global REQUEST_COUNT, SUCCESS_COUNT, ERROR_COUNT, SERVER_DOWN, log_file
            REQUEST_COUNT = SUCCESS_COUNT = ERROR_COUNT = 0
            SERVER_DOWN = False
            STOP_EVENT.clear()
            log_file = f"ddos_test_{time.strftime('%Y%m%d_%H%M%S')}.log"
            logging.getLogger().handlers = []
            logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s")

            # Configura o handler de Ctrl+C
            signal.signal(signal.SIGINT, signal_handler)

            # Inicia teste
            parsed_url = urlparse(url).netloc
            start_time = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
            print(f"\n\033[92m[INFO] Iniciando teste em {parsed_url} às {start_time}\033[0m")
            logging.info(f"Iniciando teste em {parsed_url} com {num_threads} threads e {max_requests} requisições por thread")

            threads = []
            for i in range(num_threads):
                thread = threading.Thread(
                    target=send_requests,
                    args=(url, max_requests, config["method"], config["post_data"]),
                    name=f"Thread-{i+1}"
                )
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            print_report()

        elif choice == "2":
            method = input("\033[92mDigite o método HTTP (GET ou POST): \033[0m").strip().upper()
            if method not in ["GET", "POST"]:
                print("\033[91m[ERRO] Método inválido. Use GET ou POST.\033[0m")
                continue
            config["method"] = method
            if method == "POST":
                config["post_data"] = input("\033[92mDigite os dados POST (ex: chave=valor, ou deixe vazio): \033[0m").strip() or None
            print(f"\033[92m[INFO] Método alterado para {method}.\033[0m")

        elif choice == "3":
            print("\033[93m[INFO] Saindo do programa. Até mais!\033[0m")
            sys.exit(0)

        else:
            print("\033[91m[ERRO] Opção inválida. Escolha 1, 2 ou 3.\033[0m")

if __name__ == "__main__":
    main()