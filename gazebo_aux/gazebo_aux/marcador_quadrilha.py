#!/usr/bin/env python3
import math
import random
import time
from typing import Optional, Tuple, List

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from robcomp_interfaces.msg import Quadrilha


def yaw_from_quaternion(q) -> float:
    """Converte quaternion de Odometry para yaw em radianos."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def angle_diff(a: float, b: float) -> float:
    """Diferença angular normalizada entre a e b, em radianos."""
    return math.atan2(math.sin(a - b), math.cos(a - b))


class MarcadorQuadrilha(Node):
    """
    Nó do Marcador da Quadrilha.

    Usa robcomp_interfaces/Quadrilha no tópico /quadrilha.
    """

    TURN_180_TOL = math.radians(20.0)
    RETURN_TOL = 0.35

    STOP_LIN_TOL = 0.04
    STOP_ANG_TOL = 0.08
    SPIN_ANG_MIN = 0.20

    INTERVAL_MIN = 20.0   # segundos mínimos entre comandos
    INTERVAL_MAX = 40.0   # segundos máximos entre comandos
    CANTADA_PERIOD = 8.0  # periodicidade das cantadas durante a espera

    CANTADAS = [
        "Marcador: Ai, ai, ai, ai… olha a sanfona tocando!",
        "Marcador: Bate o pé, saracoteia, balança que é de alegria!",
        "Marcador: Olha o forró, vixe! Todo mundo na pista!",
        "Marcador: Ai que saudade do arraial!",
        "Marcador: Ô xote danado, ninguém para de dançar!",
        "Marcador: Vai, vai, vai… mexe esse robozinho aí!",
        "Marcador: Segura na mão do par e não larga não!",
        "Marcador: Tá chegando a hora, presta atenção no marcador!",
        "Marcador: Ajunta o pessoal, que a festa tá começando!",
        "Marcador: Viva São João, viva o forró, viva a quadrilha!",
    ]

    def __init__(self):
        super().__init__("marcador_quadrilha_node")

        self.pub = self.create_publisher(Quadrilha, "/quadrilha", 10)
        self.sub = self.create_subscription(Quadrilha, "/quadrilha", self.quadrilha_callback, 10)

        self.odom_sub = self.create_subscription(Odometry, "/odom", self.odom_callback, 10)
        self.cmd_sub = self.create_subscription(Twist, "/cmd_vel", self.cmd_vel_callback, 10)

        self.timer = self.create_timer(0.2, self.timer_callback)

        self.pose_xy: Optional[Tuple[float, float]] = None
        self.yaw: Optional[float] = None
        self.last_yaw_for_integration: Optional[float] = None

        self.last_cmd_vel = Twist()

        self.attention_ok = False
        self.game_started = False
        self.finished = False

        self.sequence: List[str] = []
        self.current_event: Optional[str] = None
        self.current_type: Optional[str] = None
        self.current_color: Optional[str] = None
        self.event_start_time = 0.0

        self.turn_start_yaw: Optional[float] = None
        self.return_start_xy: Optional[Tuple[float, float]] = None

        self.cow_stage = None
        self.cow_count = 0
        self.cow_last_msg = 0.0
        self.cow_moved_while_passing = False

        self.monitor_360 = False
        self.spin_360_started = False
        self.spin_360_integrated = 0.0

        # Intervalo aleatório entre comandos
        self.waiting_next: bool = False          # True enquanto aguarda para enviar próximo evento
        self.next_event_time: float = 0.0        # quando enviar o próximo evento
        self.last_cantada_time: float = 0.0      # última vez que cantou algo durante a espera
        self._cantadas_shuffled: List[str] = []  # cópia embaralhada para não repetir cedo demais

        self.student_name: str = ""
        self.horario_inicio: float = 0.0

        self.ok = []
        self.warnings = []
        self.errors = []

        self.get_logger().info("Marcador da Quadrilha iniciado. Aguardando o robô.")

    # ---------------------------------------------------------------------
    # Callbacks de sensores
    # ---------------------------------------------------------------------

    def odom_callback(self, msg: Odometry):
        self.pose_xy = (
            msg.pose.pose.position.x,
            msg.pose.pose.position.y,
        )

        new_yaw = yaw_from_quaternion(msg.pose.pose.orientation)

        if self.monitor_360:
            if self.last_yaw_for_integration is not None:
                self.spin_360_integrated += abs(angle_diff(new_yaw, self.last_yaw_for_integration))
            self.last_yaw_for_integration = new_yaw

        self.yaw = new_yaw

    def cmd_vel_callback(self, msg: Twist):
        self.last_cmd_vel = msg

    # ---------------------------------------------------------------------
    # Comunicação
    # ---------------------------------------------------------------------

    def publish_text(self, text: str):
        msg = Quadrilha()
        msg.student_name = self.student_name
        msg.horario = self.horario_inicio
        msg.marcador = text
        self.pub.publish(msg)

        self.get_logger().info(f"Marcador publicou: {text}")

    def quadrilha_callback(self, msg: Quadrilha):
        # Ignora mensagens originadas pelo próprio marcador
        if msg.marcador:
            return

        text = msg.robo.strip()
        lower = text.lower()

        if "robcompehlegal" in lower:
            self.attention_ok = True
            self.publish_text("Marcador: Ê trem bão! RobComp é legal demais, sô! Atenção testada, bora pra quadrilha!")
            return

        if self.finished:
            return

        if not self.game_started and self.is_ready_message(lower):
            self.start_game(student_name=msg.student_name, horario=msg.horario)
            return

        if not self.current_event:
            return

        # Confirmação genérica de recebimento.
        if "recebi" in lower:
            self.ok.append(f"Robô confirmou recebimento de: {self.current_event}")
            return

        # Confirmações específicas por comando.
        if self.current_type == "ponte" and "girei" in lower and "180" in lower:
            self.validate_180()
            self.finish_current_event()
            return

        if self.current_type == "giro_360" and "girei" in lower and "360" in lower:
            self.validate_360()
            self.finish_current_event()
            return

        if self.current_type == "vaca" and "esperei" in lower and "vaca" in lower:
            self.validate_cow()
            self.finish_current_event()
            return

        if self.current_type == "casa":
            if "cheguei" in lower and "casa" in lower:
                self.ok.append(f"Robô chegou na casa {self.current_color}.")
                self.publish_text("pode voltar")
                return

            if "voltei" in lower and ("comecei" in lower or "inicio" in lower or "início" in lower):
                self.validate_return_position()
                self.finish_current_event()
                return

    def is_ready_message(self, lower: str) -> bool:
        return (
            "pronto" in lower
            or "iniciar" in lower
            or "começar" in lower
            or "quadrilha" in lower
        )

    # ---------------------------------------------------------------------
    # Lógica do jogo
    # ---------------------------------------------------------------------

    def start_game(self, student_name: str = "", horario: float = 0.0):
        self.game_started = True
        self.student_name = student_name
        self.horario_inicio = horario if horario else time.time()
        self.sequence = self.make_sequence()

        if not self.attention_ok:
            self.warnings.append("O robô iniciou sem enviar robcompehlegal antes do jogo.")

        self.publish_text("Marcador: A sanfona começou! Segue a linha e presta atenção nos comandos!")
        self.get_logger().info(f"Sequência sorteada: {self.sequence}")

    def make_sequence(self) -> List[str]:
        colors = ["vermelha", "verde", "azul"]

        base = [
            "Ponte tá quebrada",
            "Deixa a vaca passar",
            f"Volta pra casa {random.choice(colors)}",
            "Dá uma volta",
        ]

        options = [
            "Ponte tá quebrada",
            "Deixa a vaca passar",
            "Dá uma volta",
            f"Volta pra casa {random.choice(colors)}",
            f"Volta pra casa {random.choice(colors)}",
            f"Volta pra casa {random.choice(colors)}",
        ]

        while len(base) < 7:
            base.append(random.choice(options))

        random.shuffle(base)
        return base

    def timer_callback(self):
        now = time.time()

        if not self.game_started or self.finished:
            return

        if self.current_event is None:
            if self.waiting_next:
                # Canta a quadrilha enquanto espera
                if now - self.last_cantada_time >= self.CANTADA_PERIOD:
                    self._sing_cantada()
                    self.last_cantada_time = now
                # Hora de enviar o próximo evento?
                if now >= self.next_event_time:
                    self.waiting_next = False
                    if self.sequence:
                        self.send_next_event()
                    else:
                        self.end_game()
            else:
                # Primeira vez (logo após start_game) ou finish_current_event sem espera
                self._schedule_next_event(now)
            return

        if self.current_type == "vaca":
            self.handle_cow_timer(now)

        if self.current_type == "giro_360":
            self.handle_360_timer(now)

    def _schedule_next_event(self, now: float):
        """Inicia o período de espera aleatório antes do próximo comando."""
        delay = random.uniform(self.INTERVAL_MIN, self.INTERVAL_MAX)
        self.next_event_time = now + delay
        self.waiting_next = True
        self.last_cantada_time = now  # começa a contar a partir de agora
        self.get_logger().info(f"Próximo comando em {delay:.1f} s.")

    def _sing_cantada(self):
        """Publica uma frase de quadrilha aleatória (sem repetir cedo demais)."""
        if not self._cantadas_shuffled:
            self._cantadas_shuffled = list(self.CANTADAS)
            random.shuffle(self._cantadas_shuffled)
        self.publish_text(self._cantadas_shuffled.pop())

    def send_next_event(self):
        self.current_event = self.sequence.pop(0)
        self.current_type = self.classify_event(self.current_event)
        self.current_color = self.extract_color(self.current_event)
        self.event_start_time = time.time()

        self.turn_start_yaw = self.yaw
        self.return_start_xy = self.pose_xy

        self.cow_stage = None
        self.cow_count = 0
        self.cow_last_msg = 0.0
        self.cow_moved_while_passing = False

        self.monitor_360 = False
        self.spin_360_started = False
        self.spin_360_integrated = 0.0
        self.last_yaw_for_integration = self.yaw

        if self.current_type == "giro_360":
            self.monitor_360 = True

        self.publish_text(self.current_event)

        if self.current_type == "vaca":
            self.cow_stage = "passing"
            self.cow_last_msg = 0.0

    def classify_event(self, event: str) -> str:
        lower = event.lower()
        if "ponte" in lower:
            return "ponte"
        if "vaca" in lower:
            return "vaca"
        if "casa" in lower:
            return "casa"
        if "dá uma volta" in lower or "da uma volta" in lower:
            return "giro_360"
        return "desconhecido"

    def extract_color(self, event: str) -> Optional[str]:
        lower = event.lower()
        for color in ["vermelha", "verde", "azul"]:
            if color in lower:
                return color
        return None

    def finish_current_event(self):
        self.current_event = None
        self.current_type = None
        self.current_color = None
        self.monitor_360 = False
        self.last_yaw_for_integration = None
        self.waiting_next = False  # _schedule_next_event será chamado pelo timer_callback

    def end_game(self):
        self.finished = True
        self.publish_text("muito bem, pode parar")
        self.print_report()

    # ---------------------------------------------------------------------
    # Verificações
    # ---------------------------------------------------------------------

    def robot_is_stopped(self) -> bool:
        lin = abs(self.last_cmd_vel.linear.x)
        ang = abs(self.last_cmd_vel.angular.z)
        return lin <= self.STOP_LIN_TOL and ang <= self.STOP_ANG_TOL

    def handle_cow_timer(self, now: float):
        if self.cow_stage != "passing":
            return

        if not self.robot_is_stopped():
            self.cow_moved_while_passing = True

        if now - self.cow_last_msg >= 1.0:
            if self.cow_count < 3:
                self.publish_text("tá passando")
                self.cow_count += 1
                self.cow_last_msg = now
            else:
                self.publish_text("passou")
                self.cow_stage = "passed"

    def handle_360_timer(self, now: float):
        if not self.monitor_360:
            return

        ang = abs(self.last_cmd_vel.angular.z)
        if ang >= self.SPIN_ANG_MIN:
            self.spin_360_started = True

        if now - self.event_start_time > 2.0 and not self.spin_360_started:
            self.warnings.append("Após pedir 360°, o robô não começou a girar em tempo razoável.")
            self.spin_360_started = True  # evita repetir aviso

    def validate_180(self):
        if self.turn_start_yaw is None or self.yaw is None:
            self.warnings.append("Não foi possível verificar o giro de 180°: odometria indisponível.")
            return

        turned = abs(angle_diff(self.yaw, self.turn_start_yaw))
        error = abs(turned - math.pi)

        if error <= self.TURN_180_TOL:
            self.ok.append(f"Giro de 180° válido. Medido: {math.degrees(turned):.1f}°.")
        else:
            self.errors.append(
                f"Giro de 180° fora da tolerância. Medido: {math.degrees(turned):.1f}°."
            )

    def validate_360(self):
        self.monitor_360 = False

        integrated_deg = math.degrees(self.spin_360_integrated)

        if self.spin_360_started and integrated_deg >= 300.0:
            self.ok.append(f"Giro de 360° compatível. Movimento acumulado: {integrated_deg:.1f}°.")
        elif self.spin_360_started:
            self.warnings.append(
                f"Robô começou a girar após 360°, mas o giro acumulado parece baixo: {integrated_deg:.1f}°."
            )
        else:
            self.errors.append("Robô não aparentou girar após o comando de 360°.")

    def validate_cow(self):
        if self.cow_moved_while_passing:
            self.errors.append("Robô se moveu enquanto a vaca estava passando.")
        else:
            self.ok.append("Robô permaneceu parado enquanto a vaca passava.")

    def validate_return_position(self):
        if self.return_start_xy is None or self.pose_xy is None:
            self.warnings.append("Não foi possível verificar retorno: odometria indisponível.")
            return

        dx = self.pose_xy[0] - self.return_start_xy[0]
        dy = self.pose_xy[1] - self.return_start_xy[1]
        dist = math.hypot(dx, dy)

        if dist <= self.RETURN_TOL:
            self.ok.append(f"Retorno válido. Distância ao ponto inicial: {dist:.2f} m.")
        else:
            self.errors.append(
                f"Retorno fora da tolerância. Distância ao ponto inicial: {dist:.2f} m."
            )

    def print_report(self):
        self.get_logger().info("===== RELATÓRIO DO MARCADOR =====")
        self.get_logger().info(f"Aluno: {self.student_name or '(não informado)'}")
        self.get_logger().info(f"Horário de início: {self.horario_inicio:.9f}")

        self.get_logger().info("OK:")
        for item in self.ok:
            self.get_logger().info(f"  - {item}")

        self.get_logger().info("Avisos:")
        for item in self.warnings:
            self.get_logger().warn(f"  - {item}")

        self.get_logger().info("Erros:")
        for item in self.errors:
            self.get_logger().error(f"  - {item}")

        self.get_logger().info("===== FIM DO RELATÓRIO =====")


def main(args=None):
    rclpy.init(args=args)
    node = MarcadorQuadrilha()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()