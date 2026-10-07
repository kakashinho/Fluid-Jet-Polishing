import serial
import time
import pandas as pd
import os

# ================= CONFIG =================
PORTA_ESP32 = 'COM6'
BAUD_RATE = 115200
TEMPO_GRAVACAO = 60

SALVAR_A_CADA = 20

timestamp = int(time.time())

# ================= PASTA =================
PASTA_DADOS = "logs_pid"

os.makedirs(PASTA_DADOS, exist_ok=True)

nome_arquivo = os.path.join(
    PASTA_DADOS,
    f"dados_pid_{timestamp}.csv"
)

# ================= SERIAL =================
try:
    ser_esp32 = serial.Serial(PORTA_ESP32, BAUD_RATE, timeout=1)

    time.sleep(2)

    ser_esp32.reset_input_buffer()

    print(f"Conectado ao ESP32 na porta {PORTA_ESP32}")

except Exception as e:
    print(f"Erro ao conectar: {e}")
    exit()

# ================= ARMAZENAMENTO =================
dados_buffer = []

# Controle do cabeçalho CSV
arquivo_existe = False

print(f"Gravando dados por {TEMPO_GRAVACAO} segundos...")

inicio = time.time()

try:
    while (time.time() - inicio) < TEMPO_GRAVACAO:

        if ser_esp32.in_waiting > 0:

            linha = ser_esp32.readline().decode(
                'utf-8',
                errors='ignore'
            ).strip()

            if linha:

                valores = linha.split(',')

                if len(valores) == 5:

                    try:
                        tempo_ms = int(valores[0])
                        setpoint = float(valores[1])
                        pressao = float(valores[2])
                        duty = int(valores[3])
                        erro = float(valores[4])

                        dados_buffer.append([
                            tempo_ms,
                            setpoint,
                            pressao,
                            duty,
                            erro
                        ])

                        print(
                            f"Tempo: {tempo_ms} ms | "
                            f"SP: {setpoint:.2f} bar | "
                            f"PV: {pressao:.2f} bar | "
                            f"Duty: {duty} | "
                            f"Erro: {erro:.3f}"
                        )

                        # ================= SALVAMENTO PARCIAL =================
                        if len(dados_buffer) >= SALVAR_A_CADA:

                            df = pd.DataFrame(dados_buffer, columns=[
                                "Tempo_ms",
                                "Setpoint_bar",
                                "PressaoMedia_bar",
                                "Duty_Aplicado",
                                "Erro_bar"
                            ])

                            df.to_csv(
                                nome_arquivo,
                                mode='a',
                                header=not arquivo_existe,
                                index=False
                            )

                            arquivo_existe = True

                            print(
                                f"{len(dados_buffer)} registros salvos."
                            )

                            # limpa RAM
                            dados_buffer.clear()

                    except ValueError:
                        continue

except KeyboardInterrupt:
    print("\nGravação interrompida pelo usuário!")

# ================= FINALIZA =================
ser_esp32.close()

# Salva o restante do buffer
if len(dados_buffer) > 0:

    df = pd.DataFrame(dados_buffer, columns=[
        "Tempo_ms",
        "Setpoint_bar",
        "PressaoMedia_bar",
        "Duty_Aplicado",
        "Erro_bar"
    ])

    df.to_csv(
        nome_arquivo,
        mode='a',
        header=not arquivo_existe,
        index=False
    )

    print(f"{len(dados_buffer)} registros finais salvos.")

print(f"Arquivo final salvo em:\n{nome_arquivo}")