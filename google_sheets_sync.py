import subprocess
import json
import os

# ID da planilha criada: 1blvQMGfrchxj-1CGfHYYklMdkYMJJqZcmKPuNNrndxw
SPREADSHEET_ID = "1blvQMGfrchxj-1CGfHYYklMdkYMJJqZcmKPuNNrndxw"

def sync_to_sheets(tabela, dados):
    """
    Sincroniza uma linha de dados com o Google Sheets usando o gws CLI.
    Se falhar, apenas loga o erro e não quebra o cadastro principal.
    """
    try:
        # Verificar se o gws está instalado
        result = subprocess.run(["gws", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️ gws CLI não encontrado. Sincronização com Google Sheets ignorada.")
            return False

        # Preparar os valores para a planilha
        if tabela == "atendimentos":
            # Ordem: ID, Atendente, Data, Pedido, Cliente, Valor, Arquivo, Registro
            valores = [
                str(dados.get("id", "")),
                str(dados.get("atendente", "")),
                str(dados.get("data_atendimento", "")),
                str(dados.get("numero_pedido", "")),
                str(dados.get("nome_cliente", "")),
                str(dados.get("valor_pedido", "")),
                str(dados.get("arquivo_comprovante", "")),
                str(dados.get("data_hora_registro", ""))
            ]
        elif tabela == "pagamentos":
            # Ordem: ID, OS, Atendente, Data, Cliente, Valor Prod, Entrada, Saldo, Tipo, Arquivo, Registro
            valores = [
                str(dados.get("id", "")),
                str(dados.get("numero_os", "")),
                str(dados.get("atendente", "")),
                str(dados.get("data_pagamento", "")),
                str(dados.get("nome_cliente", "")),
                str(dados.get("valor_produto", "")),
                str(dados.get("valor_entrada", "")),
                str(dados.get("valor_saldo", "")),
                str(dados.get("tipo_pagamento", "")),
                str(dados.get("arquivo_comprovante", "")),
                str(dados.get("data_hora_registro", ""))
            ]
        else:
            return False

        # Executar o comando gws para anexar a linha
        cmd = [
            "gws", "sheets", "+append",
            "--spreadsheet", SPREADSHEET_ID,
            "--json-values", json.dumps([valores])
        ]

        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except FileNotFoundError:
        print("⚠️ gws CLI não instalado. Sincronização com Google Sheets ignorada.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Erro ao sincronizar com Google Sheets: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Erro inesperado na sincronização com Google Sheets: {e}")
        return False

def inicializar_planilha():
    """
    Cria os cabeçalhos nas abas se a planilha estiver vazia.
    """
    # Cabeçalhos para Atendimentos
    header_at = [["ID", "Atendente", "Data Atendimento", "Número Pedido", "Nome Cliente", "Valor Pedido", "Arquivo Comprovante", "Data/Hora Registro"]]
    # Cabeçalhos para Pagamentos
    header_pag = [["ID", "Número OS", "Atendente", "Data Pagamento", "Nome Cliente", "Valor Produto", "Valor Entrada", "Valor Saldo", "Tipo Pagamento", "Arquivo Comprovante", "Data/Hora Registro"]]

    try:
        # Verificar se o gws está instalado
        result = subprocess.run(["gws", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            return

        subprocess.run(["gws", "sheets", "+append", "--spreadsheet", SPREADSHEET_ID, "--json-values", json.dumps(header_at)], check=True)
        subprocess.run(["gws", "sheets", "+append", "--spreadsheet", SPREADSHEET_ID, "--json-values", json.dumps(header_pag)], check=True)
    except:
        pass