# Nome completo do aluno. Deve ser preenchido em todas as publicacoes.
string nome

# Estado atual do robo.
# Valores aceitos: READY, IN_PROGRESS e STOPPED.
string status

# Erro numerico informado pelo robo.
# - erro apos interromper andar: distancia restante, em metros;
# - erro apos interromper girar: modulo do angulo restante, em graus;
# - erro apos uma forma: deriva entre as posicoes inicial e final, em metros;
# - mensagens sem uma medida: 0.0 (sem alteracao)
float64 erro

# Horario de criacao da mensagem, em segundos desde a epoca Unix,
# incluindo a parte fracionaria. Deve ser atualizado em cada publicacao.
float64 horario
