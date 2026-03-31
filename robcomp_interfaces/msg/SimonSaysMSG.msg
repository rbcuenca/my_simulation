string student_name   # Nome do aluno que iniciou o jogo
float64 horario     # Timestamp de quando o jogo começou formato: segundos.nanosegundos
string status          # Estado do jogo ("READY", "IN_PROGRESS", "LOST", "WIN")
string lados       # Lados livres ()
string comando          # Comando atual ("SIMON_DIZ:...")
string modo_de_jogo # deixe vazio para modo normal, `deterministico` para modo determinístico