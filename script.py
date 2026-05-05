import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def extrair_fii():
    """Extrai a tabela de FIIs do Fundamentus"""
    
    # URL da busca avançada
    url = 'https://fundamentus.com.br/fii_buscaavancada.php'
    
    # Simula o formulário com todos os campos vazios + clique no botão
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
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://fundamentus.com.br/fii_buscaavancada.php'
    }
    
    # Primeiro GET para obter cookies
    session = requests.Session()
    session.get(url, headers=headers)
    
    # POST com os dados do formulário
    response = session.post(url, data=payload, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Erro na requisição: {response.status_code}")
    
    # Tenta ler a tabela
    tables = pd.read_html(response.text)
    
    for table in tables:
        if len(table.columns) >= 10:
            # Pega as primeiras 13 colunas (ignora colunas extras)
            df = table.iloc[:, :13]
            
            # Renomeia as colunas
            colunas = [
                'Papel', 'Segmento', 'Cotacao', 'FFO_Yield', 'Dividend_Yield',
                'P_VP', 'Valor_Mercado', 'Liquidez', 'Qtd_Imoveis',
                'Preco_m2', 'Aluguel_m2', 'Cap_Rate', 'Vacancia_Media'
            ]
            df.columns = colunas
            
            # Converte valores
            for col in ['Cotacao', 'P_VP', 'Valor_Mercado', 'Liquidez', 'Qtd_Imoveis', 'Preco_m2', 'Aluguel_m2']:
                df[col] = df[col].astype(str).str.replace('R\$', '').str.replace('.', '').str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            for col in ['FFO_Yield', 'Dividend_Yield', 'Cap_Rate', 'Vacancia_Media']:
                df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '.').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce') / 100
            
            # Adiciona data da coleta
            df['Data_Coleta'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return df
    
    raise Exception("Tabela não encontrada")

def main():
    print("🔄 Iniciando extração de dados...")
    
    try:
        df = extrair_fii()
        
        # Salva como CSV
        df.to_csv('fii_dados_atuais.csv', index=False)
        
        # Salva como JSON (melhor para API)
        df.to_json('fii_dados_atuais.json', orient='records', date_format='iso')
        
        # Salva como Excel
        df.to_excel('fii_dados_atuais.xlsx', index=False)
        
        # Para GitHub Actions: cria um arquivo de saída
        with open('dados_extraidos.txt', 'w') as f:
            f.write(f"{len(df)} FIIs extraídos em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"✅ {len(df)} FIIs extraídos com sucesso!")
        print(df.head(10).to_string())
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        raise

if __name__ == "__main__":
    main()
