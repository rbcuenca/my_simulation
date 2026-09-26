"""Comandante da Questao 1 da AI 2026.2.

Este arquivo deve ser instalado no pacote que inicia a simulacao. Ele usa uma
maquina de estados acionada pelo timer ``control`` e nunca bloqueia o executor
com ``sleep`` ou lacos de espera.
"""

from __future__ import annotations

import random
import time
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from robcomp_interfaces.msg import ComandanteMSG, RoboMSG


class Comandante(Node):
    """Envia a sequencia da prova e aceita as respostas como verdadeiras."""

    def __init__(self) -> None:
        super().__init__("comandante_node")

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.comando_pub = self.create_publisher(
            ComandanteMSG, "/comando", qos
        )
        self.resposta_sub = self.create_subscription(
            RoboMSG, "/resposta", self.resposta_callback, qos
        )
        self.timer = self.create_timer(0.1, self.control)

        # Parametros simples para facilitar ajustes antes da prova.
        self.declare_parameter("semente", 202602)
        self.declare_parameter("distancia_m", 2.0)
        self.declare_parameter("angulo_graus", 180.0)
        self.declare_parameter("interrupcao_min_s", 2.0)
        self.declare_parameter("interrupcao_max_s", 4.0)

        seed = self.get_parameter("semente").value
        self.rng = random.Random(seed)
        self.distancia_m = float(self.get_parameter("distancia_m").value)
        self.angulo_graus = abs(
            float(self.get_parameter("angulo_graus").value)
        )
        self.interrupcao_min_s = float(
            self.get_parameter("interrupcao_min_s").value
        )
        self.interrupcao_max_s = float(
            self.get_parameter("interrupcao_max_s").value
        )
        if self.interrupcao_min_s > self.interrupcao_max_s:
            self.interrupcao_min_s, self.interrupcao_max_s = (
                self.interrupcao_max_s,
                self.interrupcao_min_s,
            )

        self.robot_state = "aguarda_ready"
        self.state_machine = {
            "aguarda_ready": self.aguarda_ready,
            "envia_movimento": self.envia_movimento,
            "aguarda_inicio_movimento": self.aguarda_inicio_movimento,
            "aguarda_hora_parar": self.aguarda_hora_parar,
            "envia_parar": self.envia_parar,
            "aguarda_parada_movimento": self.aguarda_parada_movimento,
            "envia_erro_movimento": self.envia_erro_movimento,
            "aguarda_erro_movimento": self.aguarda_erro_movimento,
            "envia_forma": self.envia_forma,
            "aguarda_inicio_forma": self.aguarda_inicio_forma,
            "aguarda_fim_forma": self.aguarda_fim_forma,
            "envia_erro_forma": self.envia_erro_forma,
            "aguarda_deriva": self.aguarda_deriva,
            "finalizado": self.finalizado,
        }

        self.respostas: deque[RoboMSG] = deque()
        self.nome_aluno = ""
        self.movimentos: list[tuple[str, float]] = []
        self.indice_movimento = 0
        self.movimento_atual = ""
        self.forma_atual = ""
        self.instante_parada = 0.0
        self.get_logger().info("Comandante aguardando READY do robo.")

    def resposta_callback(self, msg: RoboMSG) -> None:
        """Apenas armazena respostas; as decisoes ficam na maquina de estados."""

        self.respostas.append(msg)

    def _publicar_comando(self, comando: str, valor: float = 0.0) -> None:
        msg = ComandanteMSG()
        msg.comando = comando
        msg.valor = float(valor)
        msg.horario = float(time.time())
        self.comando_pub.publish(msg)
        self.get_logger().info(
            f"Comando enviado: {comando} (valor={msg.valor:.3f})"
        )

    def _retirar_resposta(self, status: str) -> RoboMSG | None:
        """Retira a primeira resposta do aluno com o status esperado."""

        while self.respostas:
            msg = self.respostas.popleft()
            if msg.status == "READY":
                # READY sempre reinicia a sequencia, inclusive apos finalizacao.
                self._iniciar_execucao(msg)
                return None
            if self.nome_aluno and msg.nome != self.nome_aluno:
                self.get_logger().warning(
                    f"Resposta ignorada de outro aluno: {msg.nome!r}."
                )
                continue
            if msg.status == status:
                return msg
            self.get_logger().warning(
                f"Status {msg.status!r} ignorado; esperado {status!r}."
            )
        return None

    def _iniciar_execucao(self, ready: RoboMSG) -> None:
        self.nome_aluno = ready.nome
        self.respostas.clear()

        angulo = self.rng.choice((-self.angulo_graus, self.angulo_graus))
        self.movimentos = [
            ("andar", self.distancia_m),
            ("girar", angulo),
        ]
        self.rng.shuffle(self.movimentos)
        self.indice_movimento = 0
        self.movimento_atual = ""
        self.forma_atual = ""
        self.robot_state = "envia_movimento"
        self.get_logger().info(
            f"READY recebido de {self.nome_aluno!r}; iniciando sequencia."
        )

    def _ready_pendente(self) -> bool:
        """READY tem prioridade e pode reiniciar o Comandante em qualquer estado."""

        for msg in tuple(self.respostas):
            if msg.status == "READY":
                self.respostas.remove(msg)
                self._iniciar_execucao(msg)
                return True
        return False

    def aguarda_ready(self) -> None:
        if not self.respostas:
            return
        msg = self.respostas.popleft()
        if msg.status == "READY":
            self._iniciar_execucao(msg)

    def envia_movimento(self) -> None:
        comando, valor = self.movimentos[self.indice_movimento]
        self.movimento_atual = comando
        self.robot_state = "aguarda_inicio_movimento"
        self._publicar_comando(comando, valor)

    def aguarda_inicio_movimento(self) -> None:
        msg = self._retirar_resposta("IN_PROGRESS")
        if msg is None:
            return
        atraso = self.rng.uniform(
            self.interrupcao_min_s, self.interrupcao_max_s
        )
        self.instante_parada = time.monotonic() + atraso
        self.robot_state = "aguarda_hora_parar"
        self.get_logger().info(
            f"{self.movimento_atual} iniciado; parada em {atraso:.2f}s."
        )

    def aguarda_hora_parar(self) -> None:
        if time.monotonic() >= self.instante_parada:
            self.robot_state = "envia_parar"

    def envia_parar(self) -> None:
        self.robot_state = "aguarda_parada_movimento"
        self._publicar_comando("parar")

    def aguarda_parada_movimento(self) -> None:
        msg = self._retirar_resposta("STOPPED")
        if msg is not None:
            self.robot_state = "envia_erro_movimento"

    def envia_erro_movimento(self) -> None:
        self.robot_state = "aguarda_erro_movimento"
        self._publicar_comando("erro")

    def aguarda_erro_movimento(self) -> None:
        msg = self._retirar_resposta("STOPPED")
        if msg is None:
            return
        self.get_logger().info(
            f"Erro informado para {self.movimento_atual}: {msg.erro:.3f}"
        )
        self.indice_movimento += 1
        if self.indice_movimento < len(self.movimentos):
            self.robot_state = "envia_movimento"
        else:
            self.robot_state = "envia_forma"

    def envia_forma(self) -> None:
        self.forma_atual = self.rng.choice(("quadrado", "triangulo"))
        self.robot_state = "aguarda_inicio_forma"
        self._publicar_comando(self.forma_atual)

    def aguarda_inicio_forma(self) -> None:
        msg = self._retirar_resposta("IN_PROGRESS")
        if msg is not None:
            self.robot_state = "aguarda_fim_forma"

    def aguarda_fim_forma(self) -> None:
        msg = self._retirar_resposta("STOPPED")
        if msg is not None:
            self.robot_state = "envia_erro_forma"

    def envia_erro_forma(self) -> None:
        self.robot_state = "aguarda_deriva"
        self._publicar_comando("erro")

    def aguarda_deriva(self) -> None:
        msg = self._retirar_resposta("STOPPED")
        if msg is None:
            return
        self.get_logger().info(
            f"Deriva informada para {self.forma_atual}: {msg.erro:.3f} m"
        )
        self.robot_state = "finalizado"
        self.get_logger().info(
            f"Sequencia de {self.nome_aluno!r} finalizada."
        )

    def finalizado(self) -> None:
        # Permanece neste estado ate um novo READY reiniciar a sequencia.
        pass

    def control(self) -> None:
        """Executa uma etapa curta da maquina de estados a cada tick."""

        if self._ready_pendente():
            return
        state = self.state_machine.get(self.robot_state)
        if state is None:
            self.get_logger().error(f"Estado invalido: {self.robot_state!r}")
            self.robot_state = "aguarda_ready"
            return
        state()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Comandante()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
