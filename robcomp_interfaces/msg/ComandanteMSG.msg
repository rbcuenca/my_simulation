# Comando enviado pelo Comandante.
# Valores aceitos: andar, girar, parar, quadrado, triangulo e erro.
string comando

# Parametro numerico do comando.
# - andar: distancia em metros;
# - girar: angulo em graus, com sinal;
# - demais comandos: 0.0.
float64 valor

# Horario de criacao da mensagem, em segundos desde a epoca Unix,
# incluindo a parte fracionaria.
float64 horario
