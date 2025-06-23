/*
 * scicomm.c
 *
 *  Created on: 13 de jun de 2025
 *      Author: Guilherme Márcio Soares
 */
#include "board.h"
#include "device.h"
#include "scicomm.h"

#define NUM_PONTOS_WAVEFORM 1000


int protocolReceiveInt(unsigned int sci_base)
{
    uint16_t buffer[INT_SIZE];
    SCI_readCharArray(sci_base, buffer, INT_SIZE);
    return (buffer[0] | (buffer[1] << 8U));
}

void protocolSendInt(unsigned int sci_base,int data)
{
    uint16_t txBuf[INT_SIZE];
    txBuf[0] = (uint16_t)(data & 0x00FF);
    txBuf[1] = (uint16_t)((data >> 8U) & 0x00FF);

    SCI_writeCharArray(sci_base, txBuf, INT_SIZE);
}


void protocolReceiveWaveForm(unsigned int sci_base, int waveform[])
{
    // Primeiro, lê a quantidade de pontos que será enviada (1 int16_t)
    int num_pontos = protocolReceiveInt(sci_base);

    // Limita para evitar estouro do array
    if (num_pontos > NUM_PONTOS_WAVEFORM) {
        num_pontos = NUM_PONTOS_WAVEFORM;
    }

    // Agora lê todos os pontos
    for (int i = 0; i < num_pontos; i++) {
        waveform[i] = protocolReceiveInt(sci_base);
    }
}



void protocolSendWaveForm(unsigned int sci_base, int waveform[])
{
    uint16_t txBuf[INT_SIZE];

    for (int i = 0; i < NUM_PONTOS_WAVEFORM; i++)
    {
        txBuf[0] = (uint16_t)(waveform[i] & 0x00FF);
        txBuf[1] = (uint16_t)((waveform[i] >> 8U) & 0x00FF);
        SCI_writeCharArray(sci_base, txBuf, INT_SIZE);
    }
}



