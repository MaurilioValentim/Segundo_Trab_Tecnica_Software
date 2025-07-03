//
// Included Files
//
#include "driverlib.h"
#include "device.h"
#include "board.h"
#include "scicomm.h"
#include "math.h"

//

//

#define TAM_BUFFER_ADC 100
#define TAM_BUFFER_DAC 200
#define XTAL_FREQ 10000000

volatile int tam_buffer_adc = 100;
int dac_buffer[TAM_BUFFER_DAC];
int adc_buffer[TAM_BUFFER_ADC];
volatile float gain = 1.0f;

//
volatile Protocol_Header_t g_prot_header = {CMD_NONE,0};
volatile int tam_buffer_adc;
uint32_t clk = 20000000;
//
// Função Principal
//
void main(void)
{
    // Inicialização do dispositivo
    Device_init();
    Interrupt_initModule();
    Interrupt_initVectorTable();


    Board_init();

    // Habilita interrupções globais e de tempo real
    EINT;
    ERTM;

    while (1)
    {
        if (g_prot_header.cmd != CMD_NONE)
        {
            switch (g_prot_header.cmd)
            {
                case CMD_RECEIVE_INT:

                    tam_buffer_adc = protocolReceiveInt(SCI0_BASE);
                    clk = SysCtl_getClock(XTAL_FREQ);
                    CPUTimer_setPeriod(CPUTIMER0_BASE, clk/(50*tam_buffer_adc)-1);
                    break;

                case CMD_SEND_INT:
                    protocolSendInt(SCI0_BASE, tam_buffer_adc);
                    break;

                case CMD_RECEIVE_WAVEFORM:

                    protocolReceiveWaveForm(SCI0_BASE, dac_buffer);
                    break;

                case CMD_SEND_WAVEFORM:
                    protocolSendWaveForm(SCI0_BASE, adc_buffer);
                    break;
            }

            // Limpa status de interrupção e reseta comando
            SCI_clearInterruptStatus(SCI0_BASE, SCI_INT_RXFF);
            g_prot_header.cmd = CMD_NONE;
        }
    }
}

//
// Rotina de Interrupção da SCI (Recepção)
//
__interrupt void INT_SCI0_RX_ISR(void)
{
    uint16_t header[PROTOCOL_HEADER_SIZE];
    uint16_t cmd;

    SCI_readCharArray(SCI0_BASE, header, PROTOCOL_HEADER_SIZE);
    cmd = header[0];
    g_prot_header.data_len = header[1] | (header[2] << 8);
    g_prot_header.cmd = (cmd < CMD_COUNT)? (SCI_Command_e)cmd : CMD_NONE;

    Interrupt_clearACKGroup(INT_SCI0_RX_INTERRUPT_ACK_GROUP);
}

// DaC e ADC

__interrupt void INT_ADC0_1_ISR(void)
{
    static uint16_t cnt_adc =0;
    cnt_adc = (cnt_adc+1)%TAM_BUFFER_ADC;
    adc_buffer[cnt_adc] = ADC_readResult(ADC0_RESULT_BASE, ADC0_SOC0);
    ADC_clearInterruptStatus(ADC0_BASE, ADC_INT_NUMBER1);
    Interrupt_clearACKGroup(INT_ADC0_1_INTERRUPT_ACK_GROUP);

}

__interrupt void INT_myCPUTIMER1_ISR(void)
{
    static uint16_t cnt_dac = 0;
    DAC_setShadowValue(DAC0_BASE, (uint16_t) (gain*dac_buffer[cnt_dac]));
    cnt_dac = (cnt_dac+1)%TAM_BUFFER_DAC;
}
