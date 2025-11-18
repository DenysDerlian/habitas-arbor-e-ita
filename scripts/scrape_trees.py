import requests
from bs4 import BeautifulSoup
import csv
import time
from pathlib import Path
import re

# Configurações
BASE_URL = "https://arvores.sjc.sp.gov.br/"
CSV_FILE = Path(__file__).parent.parent / "trees_all.csv"
START_ID = 1  # Será ajustado automaticamente
END_ID = 85000  # Pode ir além de 80k para garantir
DELAY_BETWEEN_REQUESTS = 0.5  # segundos (para não sobrecarregar o servidor)
SAVE_INTERVAL = 50  # salvar a cada 50 registros

# Modo de operação: False = sem checagem de gaps (usa último ID), True = com checagem de gaps (verifica todos os IDs)
CHECK_GAPS = False  # Hardcoded para não checar gaps por enquanto

def get_last_id_from_csv():
    """Obtém o último ID já coletado no CSV"""
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 1:
                last_line = lines[-1]
                last_id = int(last_line.split(';')[0])
                return last_id
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return 0
    return 0

def get_existing_ids_from_csv():
    """Obtém todos os IDs já coletados no CSV (para modo com checagem de gaps)"""
    existing_ids = set()
    try:
        if CSV_FILE.exists():
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)  # Pula o cabeçalho
                for row in reader:
                    if row and row[0].isdigit():
                        existing_ids.add(int(row[0]))
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
    return existing_ids

def clean_text(text):
    """Limpa e normaliza o texto"""
    if text:
        return text.strip().replace('\n', ' ').replace('\r', '')
    return ""

def extract_tree_data(tree_id):
    """Extrai dados de uma árvore específica"""
    url = f"{BASE_URL}{tree_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Verifica se a página existe (não é erro 404 ou redirecionamento)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Verifica se é uma página válida de árvore
        title = soup.find('h3')
        if not title or 'Árvore:' not in title.text:
            return None
        
        data = {
            'id': tree_id,
            'nome_popular': '',
            'nome_cientifico': '',
            'dap': '',
            'altura': '',
            'data_coleta': '',
            'latitude': '',
            'longitude': '',
            'laudos': '',
            'image_sources': ''
        }
        
        # Extrai os dados da página
        content = soup.get_text()
        
        # Nome Popular
        nome_popular_match = re.search(r'Nome Popular:\s*([^\n]+)', content)
        if nome_popular_match:
            data['nome_popular'] = clean_text(nome_popular_match.group(1))
        
        # Nome Científico
        nome_cientifico_match = re.search(r'Nome Científico:\s*([^\n]+)', content)
        if nome_cientifico_match:
            # Remove formatação de itálico se houver
            nome_cient = clean_text(nome_cientifico_match.group(1))
            data['nome_cientifico'] = nome_cient.replace('_', '').strip()
        
        # DAP
        dap_match = re.search(r'DAP[^:]*:\s*([^\n]+)', content)
        if dap_match:
            data['dap'] = clean_text(dap_match.group(1))
        
        # Altura
        altura_match = re.search(r'Altura:\s*([^\n]+)', content)
        if altura_match:
            data['altura'] = clean_text(altura_match.group(1))
        
        # Data da Coleta
        data_match = re.search(r'Data da Coleta:\s*([^\n]+)', content)
        if data_match:
            data['data_coleta'] = clean_text(data_match.group(1))
        
        # Latitude e Longitude
        lat_long_match = re.search(r'Latitude:\s*([^\s]+)\s*/\s*Longitude:\s*([^\n]+)', content)
        if lat_long_match:
            data['latitude'] = clean_text(lat_long_match.group(1))
            data['longitude'] = clean_text(lat_long_match.group(2))
        
        # Laudos (procura por links de laudos)
        laudos = []
        laudo_links = soup.find_all('a', href=re.compile(r'/Arvore/DownloadLaudo/'))
        for link in laudo_links:
            laudos.append(link['href'])
        data['laudos'] = ', '.join(laudos) if laudos else ''
        
        # Imagens
        images = []
        img_links = soup.find_all('a', href=re.compile(r'/Arvore/DownloadImg/'))
        for link in img_links:
            images.append(link['href'])
        
        # Também procura por imagens diretas
        img_tags = soup.find_all('img', src=re.compile(r'IMG-'))
        for img in img_tags:
            if img.get('src'):
                images.append(img['src'])
        
        data['image_sources'] = ', '.join(images) if images else ''
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar ID {tree_id}: {e}")
        return None
    except Exception as e:
        print(f"Erro ao processar ID {tree_id}: {e}")
        return None

def append_to_csv(data):
    """Adiciona uma linha ao CSV"""
    with open(CSV_FILE, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            data['id'],
            data['nome_popular'],
            data['nome_cientifico'],
            data['dap'],
            data['altura'],
            data['data_coleta'],
            data['latitude'],
            data['longitude'],
            data['laudos'],
            data['image_sources']
        ])

def run_scraper(check_gaps=None, verbose=True):
    """
    Executa o scraper e retorna estatísticas
    
    Args:
        check_gaps: Se True, verifica todos os IDs existentes. Se False, usa apenas o último ID.
                   Se None, usa o valor de CHECK_GAPS.
        verbose: Se True, imprime logs. Se False, executa silenciosamente.
    
    Returns:
        dict: Estatísticas da coleta {'collected': int, 'not_found': int, 'skipped': int}
    """
    if check_gaps is None:
        check_gaps = CHECK_GAPS
    
    if verbose:
        print("=" * 60)
        print("Web Scraper - Árvores de São José dos Campos")
        print("=" * 60)
    
    collected = 0
    not_found = 0
    skipped = 0
    consecutive_not_found = 0
    max_consecutive_not_found = 100  # Para após 100 IDs consecutivos não encontrados
    
    # Determina o ID inicial baseado no modo
    if check_gaps:
        # Modo com checagem de gaps: verifica todos os IDs existentes
        if verbose:
            print("\nCarregando IDs já coletados...")
        existing_ids = get_existing_ids_from_csv()
        if verbose:
            print(f"Encontrados {len(existing_ids)} IDs já no CSV.")
        
        if existing_ids:
            min_id = min(existing_ids)
            max_id = max(existing_ids)
            if verbose:
                print(f"Faixa de IDs no CSV: {min_id} a {max_id}")
        
        start_id = START_ID
        if verbose:
            print(f"\nModo: COM checagem de gaps")
            print(f"Iniciando coleta a partir do ID: {start_id}")
    else:
        # Modo sem checagem de gaps: usa apenas o último ID
        last_id = get_last_id_from_csv()
        start_id = last_id + 1
        existing_ids = set()
        if verbose:
            print(f"\nModo: SEM checagem de gaps")
            print(f"Último ID no CSV: {last_id}")
            print(f"Iniciando coleta a partir do ID: {start_id}")
    
    if verbose:
        print(f"ID final: {END_ID}")
        print("-" * 60)
    
    for tree_id in range(start_id, END_ID + 1):
        # Se estiver checando gaps, pula IDs já coletados
        if check_gaps and tree_id in existing_ids:
            skipped += 1
            if verbose and skipped % 1000 == 0:
                print(f"Pulados: {skipped} (já coletados) | Coletados: {collected} | Não encontrados: {not_found}")
            continue
        
        if verbose:
            print(f"\nColetando ID {tree_id}...", end=' ')
        
        data = extract_tree_data(tree_id)
        
        if data:
            append_to_csv(data)
            if check_gaps:
                existing_ids.add(tree_id)  # Adiciona ao conjunto para evitar duplicatas na mesma execução
            collected += 1
            consecutive_not_found = 0
            if verbose:
                print(f"✓ Coletado ({collected} total)")
            
            # Log a cada 10 registros
            if verbose and collected % 10 == 0:
                print(f"\n{'='*60}")
                print(f"Progresso: {collected} árvores coletadas")
                if check_gaps:
                    print(f"Pulados (já coletados): {skipped}")
                print(f"Não encontrados: {not_found}")
                print(f"{'='*60}")
        else:
            not_found += 1
            consecutive_not_found += 1
            if verbose:
                print(f"✗ Não encontrado")
            
            # Para se houver muitos IDs consecutivos não encontrados
            if consecutive_not_found >= max_consecutive_not_found:
                if verbose:
                    print(f"\n{'='*60}")
                    print(f"AVISO: {max_consecutive_not_found} IDs consecutivos não encontrados.")
                    print(f"Provavelmente chegamos ao fim do cadastro.")
                    print(f"Último ID válido: {tree_id - max_consecutive_not_found}")
                    print(f"{'='*60}")
                break
        
        # Aguarda entre requisições para não sobrecarregar o servidor
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    if verbose:
        print("\n" + "=" * 60)
        print("Coleta finalizada!")
        print(f"Total de árvores coletadas: {collected}")
        if check_gaps:
            print(f"IDs pulados (já coletados): {skipped}")
        print(f"IDs não encontrados: {not_found}")
        print(f"CSV salvo em: {CSV_FILE}")
        print("=" * 60)
    
    return {
        'collected': collected,
        'not_found': not_found,
        'skipped': skipped if check_gaps else 0
    }

def main():
    """Função principal do scraper (para uso via linha de comando)"""
    run_scraper(check_gaps=CHECK_GAPS, verbose=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nColeta interrompida pelo usuário.")
        print("O progresso foi salvo no CSV.")
    except Exception as e:
        print(f"\nErro fatal: {e}")
        import traceback
        traceback.print_exc()

