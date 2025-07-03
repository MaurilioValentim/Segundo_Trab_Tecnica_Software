import serial
import struct
import time
import numpy as np
import matplotlib.pyplot as plt
import math
import datetime

# --- CONFIGURACOES ---
# Altere esta para a porta COM correta do seu microcontrolador
SERIAL_PORT = 'COM5'
BAUD_RATE = 115200

# Quantidade de valores da forma de onda que sera recebida
NUM_RECEIVE_WAVEFORM = 100

# Frequencia de Amostragem Base
Fundamental = 60
# Parametro do ADC ( mudar caso aumente o vetor do ADC )
amostragem = 100

# Parametros do DAC 
RESOLUCAO_DO_DAC = 12
AMOSTRAS_DO_DAC = 200 # mudar caso aumente o vetor do DAC

# --- DEFINICOES DO PROTOCOLO (devem ser identicas as do C) ---
# Comandos (do enum SCI_Command_e)
CMD_RECEIVE_INT = 1 # Comando para o PC enviar numero da Amostragem
CMD_SEND_INT    = 2 # Comando para o PC pedir numero da Amostragem
CMD_RECEIVE_WAVEFORM = 3  # Comando para Receber a Senoide
CMD_SEND_WAVEFORM = 4 # Comando para Enviar a Senoide

def main():
    """Funcao principal que gerencia a conexao e o menu do usuario."""
    print("--- Terminal de Teste SCI para 28379D ---")
    
    try:
        # Abre a porta serial usando um bloco 'with' para garantir que ela seja fechada
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as ser:
            print(f"Porta serial {SERIAL_PORT} aberta com sucesso a {BAUD_RATE} bps.")
            time.sleep(1) # Um pequeno tempo para a serial estabilizar

            while True:
                print("\n----- MENU -----")
                print("1. Enviar um numero da Amostragem")
                print("2. Receber um numero da Amostragem")
                print("3. Enviar uma Senoide")
                print("4. Receber uma Senoide")
                print("0. Sair")
                
                choice = input("Escolha uma opcao: ")

                if choice == '1':
                    send_int(ser)
                elif choice == '2':
                    receive_int(ser)
                elif choice == '3':
                    send_waveform(ser)
                elif choice == '4':
                    receive_waveform(ser)
                elif choice == '0':
                    print("Encerrando o programa.")
                    break
                else:
                    print("Opcao invalida. Tente novamente.")

    except serial.SerialException as e:
        print(f"\nERRO: Nao foi possivel abrir a porta serial '{SERIAL_PORT}'.")
        print(f"Detalhe: {e}")
        print("Verifique se a porta esta correta e se nenhum outro programa a esta usando.")

def send_int(ser_connection):
    """
    Pede um numero da Amostragem ao usuario, o empacota e envia para o microcontrolador.
    """
    try:
        num_str = input("Digite um numero da Amostragem para ENVIAR (entre 0 até 100): ")
        number_to_send = int(num_str)
        global amostragem
        amostragem = number_to_send
        # if not -32768 <= number_to_send <= 32767:
        if not 0 <= number_to_send <= 100:
            print("ERRO: O numero esta fora do range permitido para a Amostragem.")
            return

        # Empacota o COMANDO e o DADO em uma sequencia de bytes.
        # Formato: '<' (Little-endian), 'B' (byte, para o comando), 'h' (short, para o int16), 'h' para o tamanho do dado.
        packet_to_send = struct.pack('<Bhh', CMD_RECEIVE_INT, 2, number_to_send)
        
        print(f"\nEnviando pacote de {len(packet_to_send)} bytes: {packet_to_send.hex(' ')}")
        ser_connection.write(packet_to_send)
        print("Pacote enviado com sucesso.")

    except ValueError:
        print("ERRO: Entrada invalida. Por favor, digite um numero inteiro.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

def receive_int(ser_connection):
    """
    Envia um comando para o microcontrolador solicitando um dado e depois o recebe.
    """
    try:
        # 1. Envia apenas o COMANDO para solicitar o dado.
        #    O pacote tera 3 bytes.
        request_packet = struct.pack('<Bh', CMD_SEND_INT, 0)

        print(f"\nEnviando comando de solicitacao (1 byte): {request_packet.hex(' ')}")
        ser_connection.write(request_packet)

        # 2. Aguarda a resposta do microcontrolador.
        #    O 28379D deve responder enviando apenas o dado (int16_t = 2 bytes).
        print("Aguardando resposta do 28379D...")
        response_data = ser_connection.read(2)
        ser_connection.flushInput()  # Limpa o buffer de entrada

        if not response_data or len(response_data) < 2:
            print("ERRO: Nao houve resposta do microcontrolador (timeout).")
            return

        # 3. Desempacota os bytes recebidos para um inteiro.
        #    Formato: '<' (Little-endian), 'h' (short, para o int16)
        received_number = struct.unpack('<h', response_data)[0]
        global amostragem
        amostragem = received_number
        print(f"  -> Numero recebido do 28379D: {received_number}")

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

def send_waveform(ser_connection):
    """
    Gera uma senoide, envia a quantidade de pontos para o microcontrolador,
    e em seguida envia todos os pontos da forma de onda.
    """
    try:

        vetor_dac = gerador_senoidal()

        senoide_int = np.array(vetor_dac, dtype=np.int16)
        num_pontos = len(senoide_int)

        # Mostra a forma de onda
        plotagem(senoide_int)
        print(senoide_int)
        # Envia o cabeçalho com o número de pontos
        # CMD_RECEIVE_WAVEFORM = 4, data_len = 2 (pois vamos enviar só um int16 com o número de pontos)
        header_packet = struct.pack('<Bhh', CMD_RECEIVE_WAVEFORM, 2, num_pontos)
        ser_connection.write(header_packet)
        time.sleep(0.01)

        # Envia os pontos da forma de onda (sem cabeçalho por ponto)
        for valor in senoide_int:
            data_packet = struct.pack('<h', valor)  # Apenas os dados, sem comando
            ser_connection.write(data_packet)
            time.sleep(0.001)  # Pequeno delay para evitar sobrecarga no buffer

        print("Senoide enviada com sucesso.")

    except ValueError:
        print("ERRO: Entrada invalida. Por favor, digite um numero inteiro.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

def gerador_senoidal():
        
    freqs, amps_norm = parametros()

    res_dac = RESOLUCAO_DO_DAC
    max_dac_val = (2 ** res_dac) - 1
    offset = max_dac_val / 2.0

    # Define a menor frequência para basear o tempo de um ciclo
    menor_freq = min(freqs)
    periodo_base = 1 / menor_freq
    amostras_por_ciclo = AMOSTRAS_DO_DAC  
    ts = periodo_base / amostras_por_ciclo  # Intervalo de amostragem

    dac_valores = []

    for i in range(amostras_por_ciclo):
        t = i * ts  # tempo real para a amostra
        valor_senoide = 0
        for freq, amp_norm in zip(freqs, amps_norm):
            amp_dac = amp_norm * (max_dac_val / 2.0)
            valor_senoide += amp_dac * math.sin(2 * math.pi * freq * t)

        valor_total = offset + valor_senoide
        valor_total = max(0, min(valor_total, max_dac_val))  # Saturação
        dac_valores.append(int(round(valor_total)))


    return dac_valores

def parametros():
    global Fundamental  

    freqs = []
    amplitudes = []

    while True:
        try:
            freq = float(input("Digite a frequência (Hz): "))
            amp = float(input("Digite a amplitude: "))
        except ValueError:
            print("Por favor, digite valores numéricos válidos.")
            continue

        if not freqs:
            Fundamental = freq  # salva a primeira como fundamental

        freqs.append(freq)
        amplitudes.append(amp)

        continuar = input("Deseja adicionar outra frequência/amplitude? (s/n): ").strip().lower()
        if continuar != 's':
            break

    return freqs, amplitudes



def receive_waveform(ser_connection):
    """
    Solicita todos os pontos da senoide ao microcontrolador via serial.
    """
    try:
        num_points = NUM_RECEIVE_WAVEFORM
        # Envia o comando solicitando os dados da senoide
        request_packet = struct.pack('<Bh', CMD_SEND_WAVEFORM, 0)
        print(f"Enviando comando de solicitação: {request_packet.hex(' ')}")
        ser_connection.write(request_packet)

        # Espera os dados: 2 bytes por ponto
        total_bytes = num_points * 2
        response_data = ser_connection.read(total_bytes)

        if len(response_data) != total_bytes:
            print(f"ERRO: Esperado {total_bytes} bytes, mas recebeu {len(response_data)}.")
            return None

        # Desempacota todos os valores int16
        formato = f'<{num_points}h'  
        senoide_recebida = struct.unpack(formato, response_data)

        print("Todos os dados foram recebidos com sucesso.")

        senoide = retirar_valor_medio(senoide_recebida)

        # Plotagem dos Graficos
        plotagem(senoide)
        plot_fft(senoide)
        print(senoide)

    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
   
def retirar_valor_medio(senoide):
    dc = np.mean(senoide)
    resultado = np.subtract(senoide,dc)
    return resultado

def plotagem(senoide):
    plt.plot(senoide)
    plt.title("Forma de Onda Recebida do Microcontrolador")
    plt.xlabel("Amostra")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.show()

def plot_fft(signal):

    FREQ_A = amostragem*Fundamental

    res_dac = 12
    max_dac_val = (2 ** res_dac) - 1
    offset = max_dac_val / 2.0

    # Converte para inteiros (se ainda não estiver)
    signal = np.round(signal).astype(int)

    # Remove offset e normaliza a amplitude
    signal = (signal) / (max_dac_val / 2.0)
    
    #signal = np.round(signal).astype(int)
    print("Sinal para o plot FFT")
    print(signal)
    N = len(signal)
    # Transformar em inteiro
    fft_result = np.fft.fft(signal)
    fft_magnitude = np.abs(fft_result) / N
    fft_magnitude = fft_magnitude[:N//2] * 2
    freqs = np.fft.fftfreq(N, 1/FREQ_A)[:N//2]

    plt.stem(freqs, fft_magnitude)
    plt.title("FFT do Sinal")
    plt.xlabel("Frequência (Hz)")
    plt.ylabel("Magnitude")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()