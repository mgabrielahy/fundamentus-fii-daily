import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

def extrair_fii():
    """Extrai a tabela de FIIs do Fundamentus com headers realistas"""
    
    url = 'https://fundamentus.com.br/fii_buscaavancada.php'
    
    # Headers mais realistas (simula navegador real)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Dados do formulário
    payload = {
        'ffo_min': '',
        'ffo_max': '',
        'dy_min': '',
        'dy_max': '',
        'pvp_min': '',
        'pvp_max': '',
        'vmkt_min': '',
        'vmkt_max': '',
        'qtdim_min': '',
        'qtdim_max': '',
        'precom2_min': '',
        'precom2_max': '',
        'aluguelm2_min': '',
        'aluguelm2_max': '',
        'caprate_min': '',
        'caprate_max': '',
        'vacancia_min': '',
        'vacancia_max': '',
        'segmento': 'todos',
        'submit': 'BUSCAR'
    }
    
    # Usa session com timeout e retry
    session = requests.Session()
    
    # Adiciona um pouco de delay para simular humano
    time.sleep(random.uniform(1, 2))
    
    # Primeiro GET para obter cookies
    print("🔄 Obtendo página inicial...")
    response_get = session.get(url, headers=headers, timeout=30)
    
    if response_get.status_code != 200:
        raise Exception(f"Erro no GET: {response_get.status_code}")
    
    print("🔄 Enviando formulário...")
    # POST com os dados
    response = session.post(url, data=payload, headers=headers, timeout=30)
    
    print(f"📡 Status: {response.status_code}")
    
    if response.status_code != 200:
        raise Exception(f"Erro na requisição POST: {response.status_code}")
    
    # Verifica se a resposta contém a tabela
    if 'Nenhum resultado encontrado' in response.text:
        raise Exception("Nenhum resultado encontrado")
    
    # Salva HTML para debug (opcional)
    with open('debug.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    # Tenta ler a tabela com diferentes estratégias
    tables = pd.read_html(response.text)
    print(f"📊 {len(tables)} tabelas encontradas")
    
    # Procura a tabela correta
    for i, table in enumerate(tables):
        if len(table.columns) >= 10:
            print(f"✅ Tabela {i} selecionada ({len(table.columns)} colunas)")
            df = table.copy()
            break
    else:
        raise Exception("Nenhuma tabela adequada encontrada")
    
    # Pega apenas as primeiras 13 colunas (ignora extras)
    if len(df.columns) > 13:
        df = df.iloc[:, :13]
    
    # Renomeia as colunas
    colunas_padrao = [
        'Papel', 'Segmento', 'Cotacao', 'FFO_Yield', 'Dividend_Yield',
        'P_VP', 'Valor_Mercado', 'Liquidez', 'Qtd_Imoveis',
        'Preco_m2', 'Aluguel_m2', 'Cap_Rate', 'Vacancia_Media'
    ]
    df.columns = colunas_padrao[:len(df.columns)]
    
    # Converte valores numéricos
    for col in ['Cotacao', 'P_VP', 'Valor_Mercado', 'Liquidez', 'Qtd_Imoveis', 'Preco_m2', 'Aluguel_m2']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('R\$', '').str.replace(r'\.', '', regex=True).str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    for col in ['FFO_Yield', 'Dividend_Yield', 'Cap_Rate', 'Vacancia_Media']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '.').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) / 100
    
    # Adiciona data da coleta
    df['Data_Coleta'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return df

def main():
    print("🔄 Iniciando extração de dados do Fundamentus...")
    print("=" * 50)
    
    try:
        df = extrair_fii()
        
        print(f"\n✅ {len(df)} FIIs extraídos com sucesso!")
        print(f"📊 Colunas: {list(df.columns)}")
        
        # Mostra primeiros resultados
        print("\n📈 Primeiros 5 FIIs:")
        print(df[['Papel', 'Segmento', 'Cotacao', 'FFO_Yield', 'Dividend_Yield', 'P_VP', 'Liquidez']].head(10).to_string())
        
        # Salva como CSV
        df.to_csv('fii_dados_atuais.csv', index=False)
        print("\n💾 Arquivo CSV salvo: fii_dados_atuais.csv")
        
        # Salva como JSON
        df.to_json('fii_dados_atuais.json', orient='records', date_format='iso', force_ascii=False)
        print("💾 Arquivo JSON salvo: fii_dados_atuais.json")
        
        # Salva como Excel
        df.to_excel('fii_dados_atuais.xlsx', index=False)
        print("💾 Arquivo Excel salvo: fii_dados_atuais.xlsx")
        
        # Cria arquivo de metadados
        with open('metadados.txt', 'w', encoding='utf-8') as f:
            f.write(f"Data da coleta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total de FIIs: {len(df)}\n")
            f.write(f"Colunas: {', '.join(df.columns)}\n")
        
        print("\n" + "=" * 50)
        print("✅ Processo concluído com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")
        raise

if __name__ == "__main__":
    main()
